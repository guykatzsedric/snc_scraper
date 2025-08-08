"""
Investment Scraper for SNC Scraper
Handles VC investment tab scraping logic
"""
import time
import random
import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class InvestmentScraper:
    def __init__(self, scraper_instance):
        """Initialize investment scraper with reference to scraper instance"""
        self.scraper = scraper_instance
    
    def extract_investment_data(self, vc_slug):
        """Extract investment data from investments tab - integrated from investment_extractor.py"""
        print(f"💼 Extracting investments for: {vc_slug}")

        # Navigate to investments tab
        investments_url = f"https://finder.startupnationcentral.org/investor_page/{vc_slug}?section=investments"
        print(f"💼 Navigating to investment tab: {investments_url}")
        
        self.scraper.driver.get(investments_url)
        
        # Check if navigation was successful
        final_url = self.scraper.driver.current_url
        print(f"💼 Final URL after navigation: {final_url}")
        
        if "section=investments" not in final_url:
            print(f"⚠️  WARNING: Navigation may have failed - no 'section=investments' in final URL")

        # Human-like wait and scroll
        time.sleep(random.uniform(3.0, 5.0))  # Restored proper delay
        self.scraper.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(random.uniform(2.0, 3.0))  # Restored proper delay

        investments = []

        try:
            # Wait for the investment table to load
            wait = WebDriverWait(self.scraper.driver, 15)
            table_container = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "entity-auto-scroll-data-table")))
            if self.scraper.verbose:
                print("✅ Found investment table container")

            # Find all investment rows - they are <a> elements with company links
            investment_rows = table_container.find_elements(By.XPATH, ".//a[contains(@href, '/company_page/')]")
            if self.scraper.verbose:
                print(f"📊 Found {len(investment_rows)} investment rows")

            for i, row in enumerate(investment_rows):
                try:
                    # Extract data from the row structure we discovered
                    company_div = row.find_element(By.CLASS_NAME, "company")
                    spans = company_div.find_elements(By.TAG_NAME, "span")
                    divs = company_div.find_elements(By.TAG_NAME, "div")

                    # Extract date (first span)
                    date = spans[0].text.strip() if len(spans) > 0 else "N/A"

                    # Extract company name (from company div - look for bold text)
                    company_name = "N/A"
                    try:
                        company_name_element = company_div.find_element(By.XPATH,
                                                                        ".//span[@style and contains(@style, 'font-weight: 700')]")
                        company_name = company_name_element.text.strip()
                    except:
                        # Fallback: extract from href
                        href = row.get_attribute('href')
                        if href:
                            company_name = href.split('/')[-1].replace('-', ' ').title()

                    # Extract round type (look for span with "Round" in text)
                    round_type = "N/A"
                    for span in spans:
                        text = span.text.strip()
                        if "round" in text.lower() or "series" in text.lower() or "seed" in text.lower():
                            round_type = text
                            break

                    # Extract lead investor (check for green checkmark SVG)
                    lead_investor = "No"
                    try:
                        svg_element = company_div.find_element(By.XPATH,
                                                               ".//svg[@fill='#00A96E' or contains(@style, 'display:')]")
                        # Check if SVG is visible (not display:none)
                        parent_div = svg_element.find_element(By.XPATH, "./..")
                        if "display:none" not in parent_div.get_attribute("style"):
                            lead_investor = "Yes"
                    except:
                        pass

                    # Extract follow on (similar to lead investor)
                    follow_on = "No"
                    try:
                        # Look for second SVG or follow on indicator
                        follow_divs = company_div.find_elements(By.XPATH,
                                                                ".//div[contains(@style, 'width:') and contains(@style, '7%')]")
                        for div in follow_divs:
                            if "display:none" not in div.get_attribute("style"):
                                follow_on = "Yes"
                                break
                    except:
                        pass

                    # Extract total round amount (last span or from the end)
                    total_amount = "N/A"
                    try:
                        # Look for amount pattern in text
                        all_text = company_div.text
                        amount_match = re.search(r'\$[\d,.]+[KMB]?', all_text)
                        if amount_match:
                            total_amount = amount_match.group()
                        else:
                            # Fallback: get last span that might contain amount
                            if len(spans) > 3:
                                last_spans = spans[-2:]  # Check last 2 spans
                                for span in last_spans:
                                    text = span.text.strip()
                                    if '$' in text:
                                        total_amount = text
                                        break
                    except:
                        pass

                    investment = {
                        "date": date,
                        "company_name": company_name,
                        "round_type": round_type,
                        "lead_investor": lead_investor,
                        "follow_on": follow_on,
                        "total_round_amount": total_amount,
                        "company_url": row.get_attribute('href')
                    }

                    investments.append(investment)

                    # Show progress for first 10, then every 50 (only in verbose mode)
                    if self.scraper.verbose:
                        if i < 10:
                            print(f"  {i + 1}. {company_name} - {round_type} - {date}")
                        elif i % 50 == 0:
                            print(f"  ... processed {i + 1} investments ...")

                except Exception as e:
                    print(f"⚠️  Error extracting row {i + 1}: {e}")
                    continue

            # Extract additional graph data from JSON
            investment_rounds_by_sector = []
            investment_rounds_by_type = []

            try:
                page_source = self.scraper.driver.page_source

                # Extract Investment Rounds by Sector
                sector_match = re.search(r'"investmentRoundsBySector":\[(.*?)\]', page_source, re.DOTALL)
                if sector_match:
                    sector_json = '[' + sector_match.group(1) + ']'
                    investment_rounds_by_sector = json.loads(sector_json)
                    if self.scraper.verbose:
                        print(f"✅ Extracted {len(investment_rounds_by_sector)} investment sectors")

                # Extract Investment Rounds by Type
                type_match = re.search(r'"investmentsRoundsByRoundType":\[(.*?)\]', page_source, re.DOTALL)
                if type_match:
                    type_json = '[' + type_match.group(1) + ']'
                    investment_rounds_by_type = json.loads(type_json)
                    if self.scraper.verbose:
                        print(f"✅ Extracted {len(investment_rounds_by_type)} investment round types")

            except Exception as e:
                print(f"⚠️  Error extracting graph data: {e}")

            if self.scraper.verbose:
                print(f"✅ Successfully extracted {len(investments)} investments + graph data")

            return {
                "investments": investments,
                "investment_rounds_by_sector": investment_rounds_by_sector,
                "investment_rounds_by_type": investment_rounds_by_type,
                "summary": {
                    "total_investments": len(investments),
                    "total_sectors": len(investment_rounds_by_sector),
                    "total_round_types": len(investment_rounds_by_type)
                }
            }

        except Exception as e:
            print(f"❌ INVESTMENT SCRAPING FAILED for {vc_slug}")
            print(f"❌ Error: {e}")
            print(f"❌ Final URL: {self.scraper.driver.current_url}")
            print(f"❌ Page title: {self.scraper.driver.title}")
            
            # Save page source for debugging
            if self.scraper.verbose:
                print(f"❌ Page source (first 500 chars): {self.scraper.driver.page_source[:500]}")
            
            return {
                "investments": [],
                "investment_rounds_by_sector": [],
                "investment_rounds_by_type": [],
                "summary": {
                    "total_investments": 0,
                    "total_sectors": 0,
                    "total_round_types": 0
                }
            }