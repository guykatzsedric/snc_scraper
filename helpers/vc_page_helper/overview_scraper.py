"""
Overview Scraper for SNC Scraper
Handles VC overview tab scraping logic
"""
import time
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from services.scrapers.snc.helpers.session_manager import SessionManager


class OverviewScraper:
    def __init__(self, scraper_instance):
        """Initialize overview scraper with reference to scraper instance"""
        self.scraper = scraper_instance
    
    def scrape_investor_overview(self, url):
        """Extract comprehensive overview data from investor page with robust selectors"""
        print(f"📊 Scraping: {url}")
        
        # Check if we're already on the correct page (avoid unnecessary navigation)
        current_url = self.scraper.driver.current_url
        expected_path = url.split('?')[0]  # Remove query params for comparison
        current_path = current_url.split('?')[0]
        
        if current_path != expected_path:
            print(f"📊 Navigating to overview page: {url}")
            self.scraper.driver.get(url)
        else:
            print(f"📊 Already on correct page, skipping navigation")
            
        # Use session manager for delays and human behavior
        session_manager = SessionManager(self.scraper)
        session_manager.human_like_delay()
        session_manager.human_scroll()

        wait = WebDriverWait(self.scraper.driver, 20)
        try:
            # Wait for main heading (investor name)
            name = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).text.strip()
            if self.scraper.verbose:
                print("Found name:", name)

            # Extract the 12 specific fields based on ACTUAL HTML structure

            # 1. Overview (Long text) - CORRECTED SELECTOR
            overview = self.scraper.extract_data_safely([
                "//div[@id='about']",
                "//div[contains(text(), 'OurCrowd is a global investment platform')]"
            ])
            if self.scraper.verbose:
                print("Found overview:", overview)

            # 2. Founded - CORRECTED SELECTOR
            founded = self.scraper.extract_data_safely([
                "//h3[contains(text(), 'Founded')]/following-sibling::a/text",
                "//h3[contains(text(), 'Founded')]/following-sibling::*//text",
                "//h3[text()='Founded']/following-sibling::*//text"
            ])
            if self.scraper.verbose:
                print("Found founded:", founded)

            # Note: Investment rounds data extracted in investments tab

            # 5. Israeli portfolio companies - DIRECT SELECTOR (position-based)
            israeli_portfolio = self.scraper.extract_data_safely([
                "(//text[@class='blured-for-logged-out-users'])[1]",  # First blured element is 254
                "//text[@class='blured-for-logged-out-users' and text()='254']",  # Direct value match
                "//div[@class='entity-profile-labled-data-text-container']//text[@class='blured-for-logged-out-users' and text()='254']"
            ])
            if self.scraper.verbose:
                print("Found israeli_portfolio:", israeli_portfolio)

            # 6. Exits - DIRECT SELECTOR (position-based)
            exits = self.scraper.extract_data_safely([
                "(//text[@class='blured-for-logged-out-users'])[2]",  # Second blured element is 51
                "//text[@class='blured-for-logged-out-users' and text()='51']",  # Direct value match
                "//div[@class='entity-profile-labled-data-text-container']//text[@class='blured-for-logged-out-users' and text()='51']"
            ])
            if self.scraper.verbose:
                print("Found exits:", exits)

            # 7. Assets under management - DIRECT SELECTOR (position-based)
            aum = self.scraper.extract_data_safely([
                "(//text[@class='blured-for-logged-out-users'])[3]",  # Third blured element is $2.35B
                "//text[@class='blured-for-logged-out-users' and text()='$2.35B']",  # Direct value match
                "//div[@class='entity-profile-labled-data-text-container']//text[@class='blured-for-logged-out-users' and contains(text(), '$') and contains(text(), 'B')]"
            ])
            if self.scraper.verbose:
                print("Found aum:", aum)

            # 8. Funds - DIRECT SELECTOR (position-based)
            funds = self.scraper.extract_data_safely([
                "(//text[@class='blured-for-logged-out-users'])[4]",  # Fourth blured element is 42
                "//text[@class='blured-for-logged-out-users' and text()='42']",  # Direct value match
                "//div[@class='entity-profile-labled-data-text-container']//text[@class='blured-for-logged-out-users' and text()='42']"
            ])
            if self.scraper.verbose:
                print("Found funds:", funds)

            # 9. Target investment stages - DIRECT SELECTOR (position-based)
            investment_stages = self.scraper.extract_data_safely([
                "(//text[@class='blured-for-logged-out-users'])[5]",  # Fifth blured element is stages
                "//text[@class='blured-for-logged-out-users' and contains(text(), 'Early stage')]",
                # Direct value match
                "//div[@class='entity-profile-labled-data-text-container']//text[@class='blured-for-logged-out-users' and contains(text(), 'stage')]"
            ])
            if self.scraper.verbose:
                print("Found investment_stages:", investment_stages)

            # 10. Web & social links - FIXED SELECTORS
            website = self.scraper.extract_data_safely([
                "//div[@id='social-links-website-container']//a[@id='social-links-website']/@href",
                "//a[@id='social-links-website']/@href"
            ])

            linkedin = self.scraper.extract_data_safely([
                "//div[@id='social-links-icons-container']//a[contains(@href, 'linkedin.com')]/@href",
                "//a[contains(@href, 'linkedin.com')]/@href"
            ])
            facebook = self.scraper.extract_data_safely([
                "//div[@id='social-links-icons-container']//a[contains(@href, 'facebook.com')]/@href",
                "//a[contains(@href, 'facebook.com')]/@href"
            ])
            twitter = self.scraper.extract_data_safely([
                "//div[@id='social-links-icons-container']//a[contains(@href, 'twitter.com')]/@href",
                "//a[contains(@href, 'twitter.com')]/@href"
            ])

            web_social_links = {
                "website": website,
                "linkedin": linkedin,
                "facebook": facebook,
                "twitter": twitter
            }
            if self.scraper.verbose:
                print("Found web_social_links:", web_social_links)

            # 11. Locations - FIXED SELECTORS
            locations = []
            try:
                # Get all location address elements
                location_elements = self.scraper.driver.find_elements(By.XPATH,
                                                              "//div[@id='entity-location-desktop-container']//div[@class='entity-location-address-container']")
                locations = [elem.text.strip() for elem in location_elements if elem.text.strip()]
                if self.scraper.verbose:
                    print("Found locations:", locations)
            except:
                locations = []

            # 12. Industry preferences - EXTRACT FROM JSON DATA
            industries = []
            try:
                # Extract industry data from JSON embedded in page
                page_source = self.scraper.driver.page_source
                sector_match = re.search(r'"investmentRoundsBySector":\[(.*?)\]', page_source, re.DOTALL)
                if sector_match:
                    sectors_json = '[' + sector_match.group(1) + ']'
                    sectors_data = json.loads(sectors_json)
                    industries = [sector['sector'] for sector in sectors_data if sector.get('sector')]
                    if self.scraper.verbose:
                        print("Found industries from JSON:", industries)
                else:
                    if self.scraper.verbose:
                        print("No industry data found in JSON")
            except Exception as e:
                if self.scraper.verbose:
                    print(f"Error extracting industries from JSON: {e}")
                industries = []

            # Extract VC ID from URL
            vc_id = url.split('/')[-1] if '/' in url else url

            return {
                'vc_id': vc_id,
                'name': name,
                'url': url,
                'overview': overview,
                'founded': founded,
                'israeli_portfolio': israeli_portfolio,
                'exits': exits,
                'aum': aum,
                'funds': funds,
                'investment_stages': investment_stages,
                'web_social_links': str(web_social_links),
                'locations': ", ".join(locations),
                'industries': ", ".join(industries),
                'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            print("Page source (first 2000 chars):\n", self.scraper.driver.page_source[:2000])
            return None