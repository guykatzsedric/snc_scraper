"""
Search Page Helper for SNC Scraper
Handles search page navigation, VC extraction, and filtering
"""
import time
import random
import os
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from services.scrapers.snc.helpers.vc_cache_manager import VCCacheManager


# Step 2: Import cache manager for optional cache discovery


class SearchPageHelper:
    def __init__(self, scraper_instance):
        """Initialize navigation helper with reference to scraper instance"""
        self.scraper = scraper_instance
    
    def navigate_to_page(self, page_num):
        """Navigate directly to specific page using URL parameter"""
        try:
            # Construct URL with page parameter
            base_url = "https://finder.startupnationcentral.org/investors/search?&fundingtype=VC+and+Private+Equity&status=Active"
            page_url = f"{base_url}&page={page_num}"

            print(f"🔄 Navigating to page {page_num}: {page_url}")

            # Navigate to page URL
            self.scraper.driver.get(page_url)

            # Wait for page to load
            time.sleep(random.uniform(2.0, 4.0))

            # Verify page loaded by checking for investor links
            try:
                WebDriverWait(self.scraper.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/investor_page/')]"))
                )
                print(f"✅ Successfully loaded page {page_num}")

                # Simple verification: check if VC links exist on page
                try:
                    vc_elements = self.scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/investor_page/')]")
                    if vc_elements:
                        print(f"✅ Verified: {len(vc_elements)} VCs found on page {page_num}")
                        return True
                    else:
                        print(f"⚠️  No VCs found on page {page_num} - might be last page")
                        return False
                except Exception:
                    print(f"⚠️  Could not verify VCs on page {page_num}")
                    return True  # Assume success if we can't verify

            except Exception as e:
                print(f"⚠️  Page {page_num} load verification failed: {e}")
                return False

        except Exception as e:
            print(f"❌ Error navigating to page {page_num}: {e}")
            return False
    
    def extract_vc_links_from_search_page(self):
        """Extract all VC investor links from current search results page with duplicate filtering"""
        try:
            # Wait for page to load (look for investor links instead of specific container)
            wait = WebDriverWait(self.scraper.driver, 20)
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/investor_page/')]")))

            # Find all investor links directly
            investor_links = []
            link_elements = self.scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/investor_page/')]")

            for element in link_elements:
                href = element.get_attribute('href')
                if href and '/investor_page/' in href:
                    investor_links.append(href)

            # Remove duplicates within this page
            unique_links = list(set(investor_links))
            print(f"📋 Found {len(unique_links)} unique VC links on this page")

            # Load existing page data to determine what needs scraping
            existing_vcs, status = self.load_existing_page_data(self.scraper.current_page)
            
            # Filter VCs that need scraping using new logic
            vcs_to_scrape = self.filter_unscraped_vcs(unique_links, existing_vcs)
            
            print(f"✅ VCs to scrape: {len(vcs_to_scrape)}")
            return vcs_to_scrape

        except Exception as e:
            print(f"❌ Error extracting VC links: {e}")
            # Fallback: try without waiting
            try:
                link_elements = self.scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/investor_page/')]")
                investor_links = [elem.get_attribute('href') for elem in link_elements if elem.get_attribute('href')]
                unique_links = list(set(investor_links))
                print(f"📋 Fallback found {len(unique_links)} unique VC links")

                # Use same filtering logic in fallback
                existing_vcs, status = self.load_existing_page_data(self.scraper.current_page)
                vcs_to_scrape = self.filter_unscraped_vcs(unique_links, existing_vcs)
                
                print(f"✅ Fallback VCs to scrape: {len(vcs_to_scrape)}")
                return vcs_to_scrape
            except:
                return []
    
    def load_existing_page_data(self, page_num):
        """
        Load existing VC data for a specific page if it exists
        Returns: (vcs_list, status) or (None, None) if no existing data
        """
        try:
            results_dir = self.scraper.results_dir
            if not os.path.exists(results_dir):
                return None, None
            
            # Look for existing page file (in_progress or completed)
            for filename in os.listdir(results_dir):
                if filename.startswith(f'page_{page_num}_') and filename.endswith('.json'):
                    filepath = os.path.join(results_dir, filename)
                    
                    with open(filepath, 'r') as f:
                        page_data = json.load(f)
                    
                    # Handle both old and new JSON formats
                    if isinstance(page_data, dict) and "vcs" in page_data:
                        # New enhanced format with metadata
                        vcs_list = page_data["vcs"]
                        status = page_data.get("metadata", {}).get("status", "unknown")
                        print(f"📁 Loaded existing page {page_num} data: {len(vcs_list)} VCs (status: {status})")
                        return vcs_list, status
                    elif isinstance(page_data, list):
                        # Legacy format - direct VC list
                        status = "completed" if "completed" in filename else "in_progress"
                        print(f"📁 Loaded legacy page {page_num} data: {len(page_data)} VCs (status: {status})")
                        return page_data, status
            
            # No existing data found
            print(f"📄 No existing data found for page {page_num}")
            return None, None
            
        except Exception as e:
            print(f"❌ Error loading existing page data: {e}")
            return None, None
    
    def filter_unscraped_vcs(self, all_vc_links, existing_vcs):
        """
        Filter VCs that need scraping by comparing with existing data
        Args:
            all_vc_links: List of VC URLs extracted from current page
            existing_vcs: List of existing VC data from JSON
        Returns:
            List of VC URLs that need scraping
        """
        if not existing_vcs:
            # No existing data - all VCs need scraping
            print(f"🆕 New page: All {len(all_vc_links)} VCs need scraping")
            return all_vc_links
        
        # Build set of already scraped VC IDs for fast lookup
        scraped_vc_ids = set()
        for vc in existing_vcs:
            if isinstance(vc, dict):
                vc_id = vc.get('vc_id', '')
                if vc_id:
                    # Use smart status detection instead of relying on vc_status field
                    vc_status = self.determine_vc_status(vc)
                    if vc_status == 'scraped':
                        scraped_vc_ids.add(vc_id)
        
        # Filter out already scraped VCs
        vcs_to_scrape = []
        for url in all_vc_links:
            # Extract VC ID from URL
            vc_id = url.split('/')[-1] if '/' in url else url
            
            if vc_id not in scraped_vc_ids:
                vcs_to_scrape.append(url)
        
        print(f"🔄 Resume page: {len(scraped_vc_ids)} VCs already scraped, {len(vcs_to_scrape)} VCs need scraping")
        print(f"📊 Progress: {len(scraped_vc_ids)}/{len(all_vc_links)} VCs completed")
        
        return vcs_to_scrape
    
    def determine_vc_status(self, vc_data):
        """
        Determine if a VC was already scraped based on key fields
        Args:
            vc_data: Dictionary containing VC information
        Returns:
            "scraped" if VC has key data, "not_scraped" otherwise
        """
        if not isinstance(vc_data, dict):
            return "not_scraped"
        
        # Check for KEY overview fields (not all - some can be missing)
        key_overview_fields = ['founded', 'overview', 'exits', 'investment_stages']
        has_key_overview = any(vc_data.get(field) for field in key_overview_fields)
        
        # Check for investments data
        has_investments = bool(vc_data.get('investments'))
        
        if has_key_overview and has_investments:
            return "scraped"
        else:
            return "not_scraped"
    
    # ======================================================
    # STEP 2: OPTIONAL CACHE DISCOVERY METHODS
    # ======================================================
    
    def extract_vc_links_with_cache_filtering(self, enable_cache_filtering=False):
        """
        Step 2: Enhanced VC link extraction with optional cache-based filtering
        Uses existing proven URL extraction logic + adds cache filtering capability
        
        Args:
            enable_cache_filtering: If True, filter out VCs completed in cache
            
        Returns:
            List[str]: VC URLs that need scraping (same format as existing method)
        """
        try:
            print(f"🔍 Extracting VCs from page {self.scraper.current_page} (with cache filtering: {enable_cache_filtering})")
            
            # Step 1: Use existing proven URL extraction logic (UNCHANGED)
            wait = WebDriverWait(self.scraper.driver, 20)
            wait.until(EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/investor_page/')]")))
            
            # Find all investor links directly (same as existing method)
            investor_links = []
            link_elements = self.scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/investor_page/')]")
            
            for element in link_elements:
                href = element.get_attribute('href')
                if href and '/investor_page/' in href:
                    investor_links.append(href)
            
            # Remove duplicates within this page (same as existing)
            unique_links = list(set(investor_links))
            print(f"📋 Found {len(unique_links)} unique VC links on this page")
            
            # Step 2: Apply cache filtering if enabled (NEW OPTIONAL FEATURE)
            if enable_cache_filtering:
                filtered_links = self._filter_links_by_cache(unique_links)
                print(f"🔍 Cache filtering result: {len(filtered_links)}/{len(unique_links)} VCs need scraping")
                return filtered_links
            else:
                print(f"💡 Cache filtering disabled - returning all {len(unique_links)} VCs")
                return unique_links
                
        except Exception as e:
            print(f"❌ Error extracting VC links with cache filtering: {e}")
            # Fallback: try basic extraction without cache filtering
            try:
                link_elements = self.scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/investor_page/')]")
                investor_links = [elem.get_attribute('href') for elem in link_elements if elem.get_attribute('href')]
                unique_links = list(set(investor_links))
                print(f"📋 Fallback extraction: {len(unique_links)} VCs found")
                return unique_links
            except:
                return []
    
    def _filter_links_by_cache(self, vc_links):
        """
        Filter VC links using cache data (simplified and reliable)
        
        Args:
            vc_links: List of VC URLs
            
        Returns:
            List of VC URLs that are not completed in cache
        """
        try:
            cache_manager = VCCacheManager()
            
            filtered_links = []
            cache_filtered_count = 0
            
            for url in vc_links:
                # Extract slug from URL (same logic as existing system)
                slug = url.split('/')[-1] if '/' in url else url
                
                # Check if VC is completed in cache
                if cache_manager.is_vc_completed(slug):
                    cache_filtered_count += 1
                    print(f"  🔍 Cache: {slug} already completed - skipping")
                else:
                    filtered_links.append(url)
                    print(f"  ✅ Cache: {slug} needs scraping - keeping")
            
            print(f"🔍 Cache filtering summary:")
            print(f"  ⏩ Filtered out (completed): {cache_filtered_count}")
            print(f"  ✅ Still need scraping: {len(filtered_links)}")
            
            return filtered_links
            
        except Exception as e:
            print(f"❌ Error in cache filtering: {e}")
            print(f"🔄 Returning original list without cache filtering")
            # Return original list if cache filtering fails
            return vc_links
    
    # Note: Removed overcomplicated name extraction methods - names are captured during VC scraping
    
    def filter_unscraped_vcs_by_cache(self, all_vc_links, enable_cache_filtering=False):
        """
        Step 2: Enhanced filtering using cache in addition to existing logic
        
        Args:
            all_vc_links: List of VC URLs from current page
            enable_cache_filtering: If True, also filter using cache data
            
        Returns:
            List of VC URLs that need scraping
        """
        # First, use existing filtering logic (unchanged)
        existing_vcs, status = self.load_existing_page_data(self.scraper.current_page)
        vcs_to_scrape = self.filter_unscraped_vcs(all_vc_links, existing_vcs)
        
        # Optional cache-based filtering (Step 2 feature)
        if enable_cache_filtering:
            print(f"🔍 Applying additional cache-based filtering...")
            vcs_to_scrape = self._filter_links_by_cache(vcs_to_scrape)
        else:
            print(f"💡 Cache filtering disabled - using existing logic only")
        
        return vcs_to_scrape