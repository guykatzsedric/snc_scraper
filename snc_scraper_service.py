# Standard Library Imports
import json
import os
import random
import sys
import time
from datetime import datetime

from services.scrapers.snc.helpers.state_manager import StateManager

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Third Party Imports
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Local Config Imports
from user_config import get_active_user_config, get_connection_type, get_scraperapi_key, \
    get_scraperapi_country, get_user_proxy, get_user_type, get_user_agent, print_user_info

# Helper Module Imports (organized at top to avoid circular imports)
from helpers.driver_factory import create_stealth_driver, USER_AGENTS
from helpers.session_manager import SessionManager
from helpers.page_orchestrator import PageOrchestrator
from helpers.vc_page_helper.vc_orchestrator import VCOrchestrator

# Driver creation moved to helpers/driver_factory.py to avoid circular imports


class SNCVCScraper:
    def __init__(self, verbose=False, proxy=None, user_agent_pool=None, use_config=True):
        self.driver = None
        self.scraped_count = 0
        self.failed_urls = []
        self.results = []
        self.scraped_vc_ids = set()  # Track scraped VC IDs to prevent duplicates
        self.scraped_urls = set()  # Track scraped URLs to prevent duplicates
        self.rate_limit_detected = False  # Track if rate limit was hit
        self.current_page = 1  # Track current page for resume functionality
        self.current_page_vc_count = 0  # Track VCs processed on current page
        self.verbose = verbose  # Control debug print output

        # User Configuration Integration with ScraperAPI support
        if use_config:
            # Load from user_config.py
            self.user_config = get_active_user_config()
            self.connection_type = get_connection_type()
            self.scraperapi_key = get_scraperapi_key()
            self.scraperapi_country = get_scraperapi_country()
            self.proxy = proxy or get_user_proxy()
            self.user_type = get_user_type()
            self.session_proxy = None  # Will be set based on connection type
            user_agent_override = get_user_agent()
            print_user_info()  # Show current user configuration
        else:
            # Use provided parameters (backward compatibility)
            self.user_config = None
            self.connection_type = "manual"
            self.scraperapi_key = None
            self.scraperapi_country = None
            self.proxy = proxy
            self.user_type = "manual"
            self.session_proxy = None
            user_agent_override = None

        # Phase 4: Anti-detection configuration
        self.user_agent_pool = user_agent_pool or USER_AGENTS
        self.current_user_agent = user_agent_override  # Use config override if provided
        self.session_start_time = time.time()  # Track session duration

        # VC Status Tracking for resume functionality (OPTIMIZED)
        self.vc_status = {}  # Unified tracking: {"vc_id": {"status": "pending|in_progress|completed|failed", "url": url, "page": int, "attempts": 0}}

        # Simplified page tracking (OPTIMIZED - removed redundant page_status)
        self.completed_pages = set()  # Just track completed page numbers
        self.page_ownership = {}  # Track which user/browser owns which page: {page_num: {"user": str, "claimed_at": str, "status": str}}

        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")  # Unique session identifier

        self.setup_directories()

    def _verbose_print(self, message):
        """Print message only if verbose mode is enabled"""
        if self.verbose:
            print(message)

    def _set_vc_status(self, vc_id, status, url=None, discovered_on_page=None):
        """Set status for a specific VC"""
        if vc_id not in self.vc_status:
            self.vc_status[vc_id] = {
                "status": status,
                "url": url or "",
                "attempts": 0,
                "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "discovered_on_page": discovered_on_page or self.current_page
            }
        else:
            self.vc_status[vc_id]["status"] = status
            self.vc_status[vc_id]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if status == "in_progress":
                self.vc_status[vc_id]["attempts"] += 1
            # Update discovered_on_page if provided
            if discovered_on_page is not None:
                self.vc_status[vc_id]["discovered_on_page"] = discovered_on_page

    def _get_vc_status(self, vc_id):
        """Get status for a specific VC"""
        return self.vc_status.get(vc_id, {}).get("status", "pending")

    def _get_pending_vcs(self):
        """Get list of VCs that are pending or failed (need to be scraped)"""
        return [vc_id for vc_id, data in self.vc_status.items()
                if data["status"] in ["pending", "failed"]]

    def _get_completed_vcs(self):
        """Get list of VCs that have been successfully completed"""
        return [vc_id for vc_id, data in self.vc_status.items()
                if data["status"] == "completed"]

    def _update_page_completion(self, page_num):
        """Update page completion status (OPTIMIZED - simplified tracking)"""
        # Get all VCs discovered on this page
        page_vc_ids = [vc_id for vc_id, data in self.vc_status.items()
                       if data.get("discovered_on_page") == page_num]

        if not page_vc_ids:
            return  # No VCs to track for this page

        # Check if all VCs on this page are completed
        completed_count = len([vc_id for vc_id in page_vc_ids if self._get_vc_status(vc_id) == "completed"])

        # Mark page as completed if all VCs are done
        if completed_count == len(page_vc_ids) and len(page_vc_ids) > 0:
            self.completed_pages.add(page_num)
            self._verbose_print(f"✅ Page {page_num} marked as completed ({completed_count}/{len(page_vc_ids)} VCs)")
        elif page_num in self.completed_pages:
            # Remove from completed if no longer fully complete
            self.completed_pages.discard(page_num)
            self._verbose_print(f"⚠️ Page {page_num} no longer fully completed")

    def _is_page_completed(self, page_num):
        """Check if a page is completed (OPTIMIZED)"""
        return page_num in self.completed_pages

    def _is_page_complete(self, page_num):
        """Check if a page is 100% complete (all VCs completed or no VCs left to retry)"""
        page_data = self.page_status.get(page_num, {})
        if not page_data:
            return False

        # Page is complete if all VCs are completed
        return page_data.get("status") == "completed"

    def save_current_state(self, page_num=None, additional_data=None):
        """Save current VC status and session state for resume functionality (OPTIMIZED)"""
        try:
            state_data = {
                "session_id": self.session_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "current_page": page_num or self.current_page,
                "resume_page": self.current_page,
                "vc_status": self.vc_status,
                "completed_pages": list(self.completed_pages),
                "page_ownership": self.page_ownership,
                "scraped_count": self.scraped_count,
                "rate_limit_detected": self.rate_limit_detected,
                "total_vcs_tracked": len(self.vc_status),
                "completed_vcs": len(self._get_completed_vcs()),
                "pending_vcs": len(self._get_pending_vcs()),
                "user_type": self.user_type,
                "user_config": self.user_config
            }

            # Add any additional data passed in
            if additional_data:
                state_data.update(additional_data)

            # Save state with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            state_filename = f"vc_state_{timestamp}.json"
            state_path = os.path.join(self.progress_dir, state_filename)

            with open(state_path, 'w') as f:
                json.dump(state_data, f, indent=2)

            print(f"💾 State saved: {state_filename}")
            print(f"   📊 {len(self._get_completed_vcs())} completed, {len(self._get_pending_vcs())} pending VCs")

            return state_path

        except Exception as e:
            print(f"❌ Error saving state: {e}")
            return None

    def setup_directories(self):
        """Create simple directory structure for storing results"""
        # Create simple results directory
        self.results_dir = "results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)

        # Create progress directory for state files
        self.progress_dir = "progress"
        if not os.path.exists(self.progress_dir):
            os.makedirs(self.progress_dir)

        # Create final results directory
        self.final_dir = "final"
        if not os.path.exists(self.final_dir):
            os.makedirs(self.final_dir)

        print(f"📁 Using directories: {self.results_dir}/, {self.progress_dir}/, {self.final_dir}/")

    def _rotate_user_agent(self):
        """Phase 4: Rotate to a new user agent"""
        self.current_user_agent = random.choice(self.user_agent_pool)
        self._verbose_print(f"🔄 Rotated to user agent: {self.current_user_agent[:50]}...")
        return self.current_user_agent

    def _get_session_duration(self):
        """Phase 4: Get current session duration in minutes"""
        return (time.time() - self.session_start_time) / 60

    def _should_rotate_session(self):
        """Phase 4: Determine if session should be rotated based on duration"""
        session_duration = self._get_session_duration()
        # Rotate session every 45-60 minutes to avoid detection
        max_session_time = random.uniform(45, 60)
        return session_duration > max_session_time

    def _get_scraperapi_session_proxy(self):
        """Get a session-based proxy from ScraperAPI (one IP for entire session)"""
        if not self.scraperapi_key:
            print("❌ ScraperAPI key not configured")
            return None

        try:
            # ScraperAPI endpoint for getting session-based proxy
            api_url = "http://api.scraperapi.com/account"
            params = {
                "api_key": self.scraperapi_key,
                "country_code": self.scraperapi_country
            }

            # Get account info and session details
            response = requests.get(api_url, params=params, timeout=10)

            if response.status_code == 200:
                # For ScraperAPI, we use their proxy endpoint format
                session_proxy = f"http://{self.scraperapi_key}:@proxy-server.scraperapi.com:8001"

                print(f"✅ ScraperAPI session proxy obtained for {self.scraperapi_country}")
                print(f"   🌍 Country: {self.scraperapi_country}")
                print(f"   📡 Session-based IP (same for entire browser session)")

                return session_proxy
            else:
                print(f"❌ ScraperAPI error: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error getting ScraperAPI session proxy: {e}")
            return None

    # Session management methods moved to helpers/session_manager.py

    def detect_rate_limit(self):
        """Enhanced rate limit detection - catches 429 errors and various rate limit indicators"""
        # TEMPORARILY DISABLED - rate limit detection has false positives
        # TODO: Fix rate limit logic to avoid false positives from phone numbers, prices, dates, etc.
        return False
        
        try:
            # First, check HTTP status code through browser logs or page title
            page_title = self.driver.title.lower()
            if "429" in page_title or "rate limit" in page_title or "too many requests" in page_title:
                print(f"🚨 RATE LIMIT DETECTED: HTTP 429 in page title - '{self.driver.title}'")
                self.rate_limit_detected = True
                return True

            # Check current URL for error indicators
            current_url = self.driver.current_url
            if "error" in current_url.lower() or "429" in current_url:
                print(f"🚨 RATE LIMIT DETECTED: Error in URL - {current_url}")
                self.rate_limit_detected = True
                return True

            # Enhanced rate limit indicators (more comprehensive)
            rate_limit_indicators = [
                "//div[contains(text(), 'too many requests')]",
                "//div[contains(text(), 'rate limit')]",
                "//div[contains(text(), 'temporarily unavailable')]",
                "//div[contains(text(), 'service unavailable')]",
                "//h1[contains(text(), '429')]",
                "//h1[contains(text(), 'Too Many Requests')]",
                "//title[contains(text(), '429')]",
                "//div[contains(@class, 'error')]",
                "//div[contains(text(), 'Please try again later')]",
                "//div[contains(text(), 'blocked')]",
                "//div[contains(text(), 'access denied')]",
                "//*[contains(text(), 'Rate limit exceeded')]",
                "//*[contains(text(), 'Request limit')]",
                "//*[contains(text(), 'Too many requests')]"
            ]

            # Check for rate limit text indicators
            for indicator in rate_limit_indicators:
                try:
                    elements = self.driver.find_elements(By.XPATH, indicator)
                    if elements:
                        # Check if element is visible
                        visible_elements = [elem for elem in elements if elem.is_displayed()]
                        if visible_elements:
                            print(f"🚨 RATE LIMIT DETECTED: Found visible indicator - {indicator}")
                            print(f"   Text: {visible_elements[0].text[:100]}")
                            self.rate_limit_detected = True
                            return True
                except Exception:
                    continue

            # Check page source for rate limit patterns (case-insensitive)
            page_source = self.driver.page_source.lower()
            rate_limit_patterns = [
                "429", "too many requests", "rate limit", "rate-limit",
                "temporarily unavailable", "service unavailable",
                "access denied", "blocked", "request limit exceeded"
            ]

            for pattern in rate_limit_patterns:
                if pattern in page_source:
                    print(f"🚨 RATE LIMIT DETECTED: Found pattern '{pattern}' in page source")
                    self.rate_limit_detected = True
                    return True

            # Check if page is mostly empty (possible rate limit/block)
            body_text = ""
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body_text = body.text.strip()
            except:
                pass

            if len(body_text) < 100:  # Very short page content
                print(f"⚠️  Possible rate limit: Very short page content ({len(body_text)} chars)")
                # Don't automatically mark as rate limit, but warn
                if len(body_text) < 20:  # Almost empty page
                    print(f"🚨 RATE LIMIT DETECTED: Nearly empty page (likely blocked)")
                    self.rate_limit_detected = True
                    return True

            # Check if investor page loads properly (existing logic)
            try:
                # Wait briefly for page load
                time.sleep(1)  # Reduced from 2 seconds

                # Check if we can find basic VC page elements
                vc_indicators = self.driver.find_elements(By.XPATH,
                                                          "//div[contains(@class, 'investor')] | //h1 | //div[contains(text(), 'Overview')] | //a[contains(@href, 'investor_page')]")
                if not vc_indicators:
                    self._verbose_print(f"⚠️  No VC page elements found - possible rate limit")
                    # More conservative - don't immediately assume rate limit
                    return False

                return False

            except Exception as e:
                self._verbose_print(f"⚠️  Error checking page elements: {e}")
                return False

        except Exception as e:
            print(f"⚠️  Error in rate limit detection: {e}")
            return False

    def extract_data_safely(self, xpath_list, default="N/A"):
        """Robust selector strategy - try multiple selectors in order"""
        for xpath in xpath_list:
            try:
                if xpath.endswith("/@href") or xpath.endswith("/@src") or "/@" in xpath:
                    # Handle attribute extraction
                    attr_xpath = xpath.rsplit("/@", 1)[0]
                    attr_name = xpath.rsplit("/@", 1)[1]
                    element = self.driver.find_element(By.XPATH, attr_xpath)
                    return element.get_attribute(attr_name)
                else:
                    # Handle text extraction
                    element = self.driver.find_element(By.XPATH, xpath)
                    return element.text.strip()
            except:
                continue
        return default

    def scrape_investor_complete(self, url):
        """Legacy method - now redirects to helper method"""
        vc_page_helper = VCOrchestrator(self)
        return vc_page_helper.scrape_investor_complete_with_investments(url)

    def scrape_vcs_in_parallel_tabs(self, vc_urls, max_tabs=7, page_num=None):
        """Process VCs in batches with max parallel tabs (human-like) with progressive saving"""
        if not vc_urls:
            return []

        print(f"🔄 Processing {len(vc_urls)} VCs in batches of max {max_tabs} tabs...")
        original_window = self.driver.current_window_handle
        all_results = []

        # Process VCs in batches of max_tabs
        for batch_start in range(0, len(vc_urls), max_tabs):
            batch_urls = vc_urls[batch_start:batch_start + max_tabs]
            batch_num = (batch_start // max_tabs) + 1
            total_batches = (len(vc_urls) + max_tabs - 1) // max_tabs

            print(f"\n📦 Batch {batch_num}/{total_batches}: Processing {len(batch_urls)} VCs")

            # Step 1: Open all tabs in batch (human-like timing)
            opened_windows = []
            for i, url in enumerate(batch_urls):
                try:
                    print(f"  🖱️  Opening tab {i + 1}/{len(batch_urls)}: {url.split('/')[-1]}")

                    # Skip mouse movement for speed (only every 3rd tab)
                    if i % 3 == 0:
                        # Use session manager for human behavior
                        session_manager = SessionManager(self)
                        session_manager.human_mouse_move()

                    # Open new tab
                    self.driver.execute_script(f"window.open('{url}', '_blank');")

                    # Track the new window
                    all_windows = self.driver.window_handles
                    new_window = [w for w in all_windows if w != original_window and w not in opened_windows][0]
                    opened_windows.append(new_window)

                    # Human-like delay between tab opens
                    time.sleep(random.uniform(0.8, 1.5))  # Restored proper delay

                except Exception as e:
                    print(f"  ❌ Error opening tab for {url}: {e}")
                    continue

            print(f"  📱 Opened {len(opened_windows)} tabs, now processing...")

            # Step 2: Process all tabs in parallel (switch between them)
            batch_results = []
            for i, (url, window_handle) in enumerate(zip(batch_urls, opened_windows)):
                try:
                    print(f"  📊 Processing tab {i + 1}/{len(opened_windows)}: {url.split('/')[-1]}")

                    # Switch to tab
                    self.driver.switch_to.window(window_handle)

                    # Add mouse movement after switching
                    # Use session manager for human behavior
                    session_manager = SessionManager(self)
                    session_manager.human_mouse_move()

                    # Wait for page load and scrape
                    try:
                        WebDriverWait(self.driver, 12).until(
                            EC.presence_of_element_located((By.TAG_NAME, "h1"))
                        )

                        current_url = self.driver.current_url
                        print(f"    🔍 Original URL: {url}")
                        print(f"    🔍 Current URL:  {current_url}")

                        # Scrape complete data: Overview + Investments (use original URL to avoid redirect issues)
                        vc_page_helper = VCOrchestrator(self)
                        complete_data = vc_page_helper.scrape_investor_complete_with_investments(url)
                        if complete_data:
                            batch_results.append(complete_data)
                            all_results.append(complete_data)  # Add to total results immediately
                            print(f"    ✅ Completed: {complete_data['name']}")
                            
                            # Progressive saving after each VC completion
                            if page_num is not None:
                                try:
                                    self.save_page_progress(all_results, page_num)
                                    print(f"    💾 Saved progress: {len(all_results)} VCs completed")
                                except Exception as e:
                                    print(f"    ⚠️  Error saving progress: {e}")
                        else:
                            print(f"    ❌ Failed to scrape: {current_url.split('/')[-1]}")
                            # Check if this failure was due to rate limit
                            if self.rate_limit_detected:
                                print(f"    🚨 Rate limit detected during scraping - breaking from batch")
                                break
                    except Exception as e:
                        print(f"    ❌ Error scraping tab: {e}")

                    # Human-like delay between processing tabs
                    time.sleep(random.uniform(2.0, 4.0))  # Restored proper delay

                except Exception as e:
                    print(f"  ❌ Error processing tab {i + 1}: {e}")
                    continue

            # Step 3: Close all tabs in batch (human-like)
            print(f"  🗑️  Closing {len(opened_windows)} tabs...")
            for i, window_handle in enumerate(opened_windows):
                try:
                    self.driver.switch_to.window(window_handle)

                    # Human-like mouse movement for closing
                    if i % 2 == 0:  # Every other tab for realism
                        # Use session manager for human behavior
                        session_manager = SessionManager(self)
                        session_manager.human_mouse_move()

                    # Close tab
                    self.driver.close()

                    # Human-like delay between closings
                    time.sleep(random.uniform(1.0, 2.0))  # Restored proper delay

                except Exception as e:
                    print(f"    ⚠️  Error closing tab {i + 1}: {e}")
                    continue

            # Return to search page
            self.driver.switch_to.window(original_window)

            # Results already added immediately after each VC completion for progressive saving
            print(f"  📊 Batch {batch_num} completed: {len(batch_results)}/{len(batch_urls)} successful")

            # Faster delay between batches
            if batch_start + max_tabs < len(vc_urls):  # Not the last batch
                delay = random.uniform(1.0, 2.5)  # Reduced from 2.0-4.0s
                print(f"  ⏳ Resting {delay:.1f}s before next batch...")
                time.sleep(delay)

        print(f"✅ All batches completed: {len(all_results)}/{len(vc_urls)} successful")
        return all_results


    def save_page_progress(self, page_results, page_num):
        """Save progress after each page completion with CORRECT page number in filename"""
        try:
            import pandas as pd

            # Generate timestamp for filenames (YYYYMMDD_HHMMSS format)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # FIXED: Save with ACTUAL page number that was completed
            page_filename_json = f'page_{page_num}_completed_{len(page_results)}_vcs_{timestamp}.json'
            page_path = os.path.join(self.progress_dir, page_filename_json)

            # Add metadata to the JSON with ownership info
            page_data = {
                "metadata": {
                    "actual_page_number": page_num,  # ACTUAL page that was completed
                    "total_vcs_on_page": len(page_results),
                    "scraped_timestamp": timestamp,
                    "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "completed",
                    "user_type": self.user_type,
                    "session_id": self.session_id,
                    "page_ownership": self.page_ownership.get(page_num, {})
                },
                "vcs": page_results
            }

            # Save JSON for this page
            with open(page_path, 'w') as f:
                json.dump(page_data, f, indent=2)

            # Mark page as completed and release ownership
            self.completed_pages.add(page_num)
            # Page completed (user coordination removed)

            print(f"📏 Page {page_num} completed and saved: {page_filename_json}")
            print(f"   📄 {len(page_results)} VCs from ACTUAL page {page_num}")
            print(f"   💼 User: {self.user_type}")
            print(f"   📁 Location: {self.progress_dir}")

        except Exception as e:
            print(f"❌ Error saving page progress: {e}")

    def save_page_progress_with_rate_limit(self, page_results, page_num, vcs_processed, total_vcs_on_page):
        """Save partial page progress when rate limit is hit"""
        try:
            import pandas as pd

            # Generate timestamp for filenames (YYYYMMDD_HHMMSS format)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save partial page results with rate limit info
            page_filename_json = f'vc_results_{len(page_results)}_vcs_{timestamp}_page_{page_num}_PARTIAL_RATE_LIMIT.json'
            page_path = os.path.join(self.progress_dir, page_filename_json)

            # Add metadata with rate limit info
            page_data = {
                "metadata": {
                    "page_number": page_num,
                    "total_vcs_on_page": total_vcs_on_page,
                    "vcs_processed_before_rate_limit": vcs_processed,
                    "vcs_remaining": total_vcs_on_page - vcs_processed,
                    "scraped_timestamp": timestamp,
                    "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "partial_rate_limit",
                    "resume_instructions": {
                        "use_start_page": page_num,
                        "use_resume_from_vc": vcs_processed,
                        "description": f"Resume from page {page_num}, VC #{vcs_processed + 1}"
                    }
                },
                "vcs": page_results
            }

            # Save JSON for this partial page
            with open(page_path, 'w') as f:
                json.dump(page_data, f, indent=2)

            print(f"💾 PARTIAL page {page_num} saved: {page_filename_json}")
            print(f"   📊 {len(page_results)} VCs scraped before rate limit")
            print(f"   ⚠️ {total_vcs_on_page - vcs_processed} VCs remaining on page {page_num}")
            print(f"   📁 Location: {self.progress_dir}")

        except Exception as e:
            print(f"❌ Error saving partial page progress: {e}")

    def save_final_results(self, results, test_name="final"):
        """Save final results to organized directories"""
        try:
            # Generate timestamp and filename
            timestamp = datetime.now().strftime("%H%M%S")
            final_filename = f'vc_investors_{test_name}_{len(results)}_vcs_{timestamp}.json'
            final_path = os.path.join(self.final_dir, final_filename)

            # Save final JSON results
            with open(final_path, 'w') as f:
                json.dump(results, f, indent=2)

            print(f"💾 Final results saved: {final_path}")
            return final_path

        except Exception as e:
            print(f"❌ Error saving final results: {e}")
            return None

    # ======================================================
    # NEW ENHANCED FILE MANAGEMENT METHODS (ADDED)
    # ======================================================

    def save_page_with_enhanced_metadata(self, page_num, vcs, status, additional_metadata=None):
        """
        NEW: Enhanced page saving with structured metadata (like new FileManager)
        Saves in format: page_3_completed_7_vcs_142301.json
        """
        try:
            # Ensure results directory exists
            if not os.path.exists("results"):
                os.makedirs("results")

            timestamp = datetime.now().strftime("%H%M%S")

            # Remove old files with same page and different status if completing
            if status == "completed":
                self._remove_old_page_files(page_num, ["in_progress", "partial"])

            # Create structured filename
            filename = f"page_{page_num}_{status}_{len(vcs)}_vcs_{timestamp}.json"
            filepath = os.path.join("results", filename)

            # Prepare enhanced metadata structure
            page_data = {
                "metadata": {
                    "page_number": page_num,
                    "status": status,
                    "total_vcs": len(vcs),
                    "scraped_timestamp": timestamp,
                    "scrape_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "session_id": self.session_id,
                    "user_type": self.user_type,
                    "connection_type": self.connection_type,
                    "scraper_version": "enhanced_old_version"
                },
                "vcs": vcs
            }

            # Add additional metadata if provided
            if additional_metadata:
                page_data["metadata"].update(additional_metadata)

            # Save structured JSON
            with open(filepath, 'w') as f:
                json.dump(page_data, f, indent=2)

            print(f"💾 Enhanced page save: {filename}")
            return filename

        except Exception as e:
            print(f"❌ Error saving enhanced page data: {e}")
            return None

    def _remove_old_page_files(self, page_num, status_list):
        """Helper to remove old page files when updating status"""
        try:
            if not os.path.exists(self.results_dir):
                return

            for filename in os.listdir(self.results_dir):
                if filename.startswith(f'page_{page_num}_') and filename.endswith('.json'):
                    for status in status_list:
                        if f'_{status}_' in filename:
                            filepath = os.path.join(self.results_dir, filename)
                            os.remove(filepath)
                            print(f"🗑️ Removed old file: {filename}")
                            break
        except Exception as e:
            print(f"⚠️ Error removing old files: {e}")

    def load_page_with_enhanced_metadata(self, page_num):
        """
        NEW: Load page data with enhanced metadata support
        Returns: (vcs_list, status, metadata) or ([], None, None)
        """
        try:
            if not os.path.exists(self.results_dir):
                return [], None, None

            # Find page file
            for filename in os.listdir(self.results_dir):
                if filename.startswith(f'page_{page_num}_') and filename.endswith('.json'):
                    filepath = os.path.join(self.results_dir, filename)

                    with open(filepath, 'r') as f:
                        data = json.load(f)

                    # Handle both old and new formats
                    if isinstance(data, dict) and "metadata" in data and "vcs" in data:
                        # New enhanced format
                        return data["vcs"], data["metadata"]["status"], data["metadata"]
                    elif isinstance(data, dict) and "vcs" in data:
                        # Old format with some metadata
                        status = data.get("metadata", {}).get("status", "unknown")
                        return data["vcs"], status, data.get("metadata", {})
                    else:
                        # Legacy format - direct VC list
                        status = "completed" if "completed" in filename else "in_progress"
                        return data, status, {}

            return [], None, None

        except Exception as e:
            print(f"❌ Error loading page data: {e}")
            return [], None, None

    def print_status_summary(self):
        """Print comprehensive status summary including state management"""
        completed = len(self._get_completed_vcs())
        pending = len(self._get_pending_vcs())
        failed = len([vc_id for vc_id, data in self.vc_status.items() if data["status"] == "failed"])
        in_progress = len([vc_id for vc_id, data in self.vc_status.items() if data["status"] == "in_progress"])

        print(f"\n📊 === SESSION STATUS SUMMARY ===")
        print(f"✅ Completed VCs: {completed}")
        print(f"⏳ Pending VCs: {pending}")
        print(f"❌ Failed VCs: {failed}")
        print(f"🔄 In Progress VCs: {in_progress}")
        print(f"📈 Total VCs tracked: {len(self.vc_status)}")
        print(f"🆔 Session ID: {self.session_id}")
        if self.rate_limit_detected:
            print(f"🚨 Rate limit detected: YES")
        print(f"📊 ==================================")

    def close_session(self):
        if self.driver:
            self.driver.quit()
            print("🔒 Browser session closed")


def run_single_page_session():
    """Run a single page session with proper coordination and page claiming"""
    print("🎯 SNC SCRAPER - SINGLE PAGE SESSION")
    print("=" * 50)

    # Create scraper with user configuration
    scraper = SNCVCScraper(verbose=True, use_config=True)

    # Create session manager and page orchestrator
    session_manager = SessionManager(scraper)
    state_manager = StateManager(scraper)
    page_orchestrator = PageOrchestrator(scraper)

    try:

        print("\n1️⃣ Starting session and login...")
        session_manager.start_session()

        # Load previous state and get target page
        target_page = state_manager.load_previous_state()
        print(f"\n🎯 Target page: {target_page}")

        # Process exactly one page using PageOrchestrator
        results, last_page = page_orchestrator.scrape_pages(
            start_page=target_page,
            end_page=target_page,  # Process only one page
            max_tabs=7,
        )

        if results:
            print(f"\n🎉 Successfully completed page {last_page}!")
            scraper.save_final_results(results, f"page_{last_page}_user_{scraper.user_type}")
            scraper.print_status_summary()
        else:
            print(f"\n⚠️  No results from page {target_page}")
            scraper.print_status_summary()

        print(f"\n✅ SESSION COMPLETE - Page {target_page} processed")
        print("💡 Next steps:")
        print("   1. Switch ACTIVE_USER in user_config.py")
        print("   2. Run this script again for different pages")
        print("   3. Or run same user again for next assigned page")

    except KeyboardInterrupt:
        print("\n⏹️  Session interrupted - saving state...")
        scraper.save_current_state()

    except Exception as e:
        print(f"❌ Error during session: {e}")
        scraper.save_current_state()

    finally:
        scraper.close_session()


if __name__ == "__main__":
    # Enhanced main execution with new features
    print("🎯 SNC SCRAPER")
    print("=" * 40)
    print()

    run_single_page_session()
