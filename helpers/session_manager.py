"""
Session Manager for SNC Scraper
Handles browser session initialization, proxy setup, and authentication
"""
import random

import requests
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from services.scrapers.snc.helpers.driver_factory import create_stealth_driver


class SessionManager:
    def __init__(self, scraper_instance):
        """Initialize session manager with reference to scraper instance"""
        self.scraper = scraper_instance

    def _verbose_print(self, message):
        """Print message only if verbose mode is enabled"""
        if self.scraper.verbose:
            print(message)

    def _rotate_user_agent(self):
        """Phase 4: Rotate to a new user agent"""
        self.scraper.current_user_agent = random.choice(self.scraper.user_agent_pool)
        self._verbose_print(f"🔄 Rotated to user agent: {self.scraper.current_user_agent[:50]}...")
        return self.scraper.current_user_agent

    def _get_scraperapi_session_proxy(self):
        """Get a session-based proxy from ScraperAPI (one IP for entire session)"""
        if not self.scraper.scraperapi_key:
            print("❌ ScraperAPI key not configured")
            return None

        try:
            # ScraperAPI endpoint for getting session-based proxy
            api_url = "http://api.scraperapi.com/account"
            params = {
                "api_key": self.scraper.scraperapi_key,
                "country_code": self.scraper.scraperapi_country
            }

            # Get account info and session details
            response = requests.get(api_url, params=params, timeout=10)

            if response.status_code == 200:
                # For ScraperAPI, we use their proxy endpoint format
                session_proxy = f"http://{self.scraper.scraperapi_key}:@proxy-server.scraperapi.com:8001"

                print(f"✅ ScraperAPI session proxy obtained for {self.scraper.scraperapi_country}")
                print(f"   🌍 Country: {self.scraper.scraperapi_country}")
                print(f"   📡 Session-based IP (same for entire browser session)")

                return session_proxy
            else:
                print(f"❌ ScraperAPI error: {response.status_code}")
                print(f"   Response: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error getting ScraperAPI session proxy: {e}")
            return None

    def _setup_session_proxy(self):
        """Setup session proxy based on connection type"""
        if self.scraper.connection_type == "scraperapi":
            print("🔄 Setting up ScraperAPI session-based proxy...")
            self.scraper.session_proxy = self._get_scraperapi_session_proxy()
            if not self.scraper.session_proxy:
                print("⚠️  Falling back to direct connection")
                self.scraper.session_proxy = None
        elif self.scraper.connection_type == "proxy":
            print(f"🔗 Using configured proxy: {self.scraper.proxy}")
            self.scraper.session_proxy = self.scraper.proxy
        else:
            print("🌐 Using direct connection")
            self.scraper.session_proxy = None

        return self.scraper.session_proxy

    def verify_login(self):
        """Verify user is logged in"""
        try:
            self.scraper.driver.find_element(By.XPATH, "//a[contains(@href, 'watchlist')]")
            print("✅ Successfully authenticated")
            return True
        except Exception:
            print("⚠️  Not authenticated - some data may be limited")
            return False

    def start_session(self):
        """Start browser session with proxy and authentication"""
        print("🚀 Starting enhanced stealth browser session...")

        # Setup session-based proxy (ScraperAPI or regular proxy)
        session_proxy = self._setup_session_proxy()

        # Phase 4: Use enhanced driver with anti-detection
        user_agent = self._rotate_user_agent()
        self.scraper.driver = create_stealth_driver(proxy=session_proxy, user_agent=user_agent)

        if session_proxy:
            if self.scraper.connection_type == "scraperapi":
                print(f"🌍 Using ScraperAPI with country: {self.scraper.scraperapi_country}")
                print(f"📡 Session-based IP (consistent for entire session)")
            else:
                print(f"🔗 Using proxy: {session_proxy}")
        else:
            print("🌐 Direct connection (no proxy)")

        print(f"🎭 Using user agent: {user_agent[:50]}...")

        self.scraper.driver.get("https://finder.startupnationcentral.org")

        # Phase 4: Extended delay after initial load
        self.extended_delay()

        # Manual login
        print("👤 Please log in manually in the browser window.")
        print("   💡 Use the appropriate user account for this session:")
        if self.scraper.user_type == "rate_limited":
            print("   🔴 Rate-limited user (for odd pages)")
        elif self.scraper.user_type == "fresh":
            print("   🟢 Fresh user (for even pages)")

        input("Press Enter here after you have completed login...")

        self.verify_login()

    def human_scroll(self):
        """Phase 4: Enhanced human-like scrolling with varied patterns"""
        # Use own delay methods

        scroll_amount = random.randint(300, 800)
        self.scraper.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.micro_delay()  # Use own delay method

        # Phase 4: More varied scroll patterns
        if random.random() < 0.3:  # Increased probability for more human-like behavior
            scroll_back = random.randint(100, 300)
            self.scraper.driver.execute_script(f"window.scrollBy(0, -{scroll_back});")
            self.micro_delay()

        # Phase 4: Occasional pause to "read" content
        if random.random() < 0.1:
            self.human_like_delay(min_delay=1, max_delay=3)

    def human_mouse_move(self):
        """Phase 4: Human-like mouse movement simulation"""
        # Use already imported function

        try:
            # Phase 4: Random mouse movement to simulate real user behavior
            actions = ActionChains(self.scraper.driver)

            # Get current window size
            window_size = self.scraper.driver.get_window_size()
            max_x = window_size['width'] - 100
            max_y = window_size['height'] - 100

            # Random movement pattern
            if random.random() < 0.7:  # 70% chance of simple movement
                # Simple random movement
                x_offset = random.randint(-200, 200)
                y_offset = random.randint(-200, 200)
                actions.move_by_offset(x_offset, y_offset)
            else:
                # More complex movement pattern
                for _ in range(random.randint(2, 4)):
                    x_offset = random.randint(-100, 100)
                    y_offset = random.randint(-100, 100)
                    actions.move_by_offset(x_offset, y_offset)
                    actions.pause(random.uniform(0.1, 0.3))

            actions.perform()
            self.micro_delay()

            # Reset mouse to safe position (center)
            actions = ActionChains(self.scraper.driver)
            actions.move_to_element_with_offset(
                self.scraper.driver.find_element("tag name", "body"),
                max_x // 2, max_y // 2
            )
            actions.perform()

        except Exception as e:
            # Don't let mouse movement errors break the scraping
            if self.scraper.verbose:
                print(f"⚠️  Mouse movement error (non-critical): {e}")
            pass
    
    # Delay methods moved from main service (exact same logic)
    def human_like_delay(self, min_delay=2, max_delay=5):
        """Phase 4: Enhanced human-like delay with configurable range"""
        import time
        import random
        time.sleep(random.uniform(min_delay, max_delay))

    def extended_delay(self):
        """Phase 4: Longer delay for sensitive operations"""
        import time
        import random
        time.sleep(random.uniform(5, 10))

    def micro_delay(self):
        """Phase 4: Short delay for quick operations"""
        import time
        import random
        time.sleep(random.uniform(0.5, 1.5))
