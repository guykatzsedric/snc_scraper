"""
VC Orchestrator for SNC Scraper
Main VC scraping flow controller - orchestrates overview and investment tab scraping
"""
from services.scrapers.snc.helpers.vc_page_helper.investment_scraper import InvestmentScraper
from services.scrapers.snc.helpers.vc_page_helper.overview_scraper import OverviewScraper


class VCOrchestrator:
    def __init__(self, scraper_instance):
        """Initialize VC orchestrator with reference to scraper instance"""
        self.scraper = scraper_instance
        self.overview_scraper = OverviewScraper(scraper_instance)
        self.investment_scraper = InvestmentScraper(scraper_instance)

    def scrape_investor_complete_with_investments(self, url):
        """Complete VC scraping: Overview tab → Investments tab → Exit with status tracking and rate limit detection"""
        vc_id = url.split('/')[-1] if '/' in url else url

        # Check if already completed
        if self.scraper._get_vc_status(vc_id) == "completed":
            self.scraper._verbose_print(f"🔄 VC {vc_id} already completed - skipping")
            return None

        # Mark as in progress
        self.scraper._set_vc_status(vc_id, "in_progress", url)
        print(f"🏢 === SCRAPING VC: {vc_id} ===")

        # Step 1: Check for rate limits immediately
        if self.scraper.detect_rate_limit():
            print(f"🚨 RATE LIMIT DETECTED on {vc_id} - stopping gracefully")
            self.scraper._set_vc_status(vc_id, "failed")  # Mark as failed due to rate limit
            self.scraper.rate_limit_detected = True
            return None

        # NEW: Step 1.5: Early validation - check for problematic VC types
        validation_result = self._validate_vc_page(vc_id)
        if validation_result['status'] != 'valid':
            print(f"⚠️ VC {vc_id} is {validation_result['status']}: {validation_result['reason']}")
            return validation_result  # Return status object instead of None

        # Step 2: Extract Overview tab data (already on page from tab opening)
        print("📊 Step 1: Extracting Overview data...")
        overview_data = self.overview_scraper.scrape_investor_overview(url)
        if not overview_data:
            print("❌ Failed to extract overview data - skipping VC")
            self.scraper._set_vc_status(vc_id, "failed")  # Mark as failed
            return None

        # Step 2: Extract VC slug for investments URL (handle query parameters)
        vc_slug = url.split('?')[0].split('/')[-1] if '/' in url else url
        print(f"💼 VC slug extracted: {vc_slug}")
        print(
            f"💼 Investment URL will be: https://finder.startupnationcentral.org/investor_page/{vc_slug}?section=investments")

        # Step 3: Extract Investments tab data
        print("💼 Step 2: Extracting Investment data...")
        investment_data = self.investment_scraper.extract_investment_data(vc_slug)

        # Step 4: Combine all data into final structure
        complete_data = {
            # Overview data
            **overview_data,
            # Investment data
            "investments": investment_data["investments"],
            "investment_rounds_by_sector_detailed": investment_data["investment_rounds_by_sector"],
            "investment_rounds_by_type_detailed": investment_data["investment_rounds_by_type"],
            "investment_summary": investment_data["summary"]
        }

        # Step 5: Mark as completed and update tracking
        self.scraper._set_vc_status(vc_id, "completed", url)
        self.scraper.scraped_urls.add(url)
        self.scraper.scraped_vc_ids.add(vc_id)
        self.scraper.scraped_count += 1

        print(f"✅ Step 3: Completed VC {self.scraper.scraped_count}: {overview_data['name']}")
        print(f"   - Overview: ✅ ({len([k for k, v in overview_data.items() if v != 'N/A'])}/15 fields)")
        print(f"   - Investments: ✅ ({investment_data['summary']['total_investments']} investments)")
        print(
            f"   - Graph data: ✅ ({investment_data['summary']['total_sectors']} sectors, {investment_data['summary']['total_round_types']} round types)")
        print(f"🔄 Status: completed (Total: {len(self.scraper._get_completed_vcs())} completed VCs)")
        print(f"🏢 === COMPLETED: {overview_data['name']} ===\n")

        return complete_data
    
    def _validate_vc_page(self, vc_id):
        """
        Validate VC page for problematic content before scraping
        Checks for inactive or limited information indicators
        
        Args:
            vc_id: VC identifier for logging
            
        Returns:
            dict: Validation result with status and reason
        """
        try:
            # Get current page source
            page_source = self.scraper.driver.page_source.lower()
            
            # Check for inactive VC indicator
            if "presumed inactive no recent investments in israel" in page_source:
                return {
                    'status': 'inactive',
                    'name': 'Inactive VC (Not Scraped)',
                    'vc_id': vc_id,
                    'url': self.scraper.driver.current_url,
                    'reason': 'PRESUMED INACTIVE No recent investments in Israel',
                    'validation_type': 'inactive',
                    'scraped_at': '',
                    'overview': '',
                    'investments': []
                }
            
            # Check for limited information indicator  
            if "this profile has limited information" in page_source:
                return {
                    'status': 'limited_info',
                    'name': 'Limited Info VC (Not Scraped)',
                    'vc_id': vc_id,
                    'url': self.scraper.driver.current_url,
                    'reason': 'This profile has limited information',
                    'validation_type': 'limited_info',
                    'scraped_at': '',
                    'overview': '',
                    'investments': []
                }
            
            # VC is valid for scraping
            return {
                'status': 'valid',
                'reason': 'VC page is valid for scraping',
                'vc_id': vc_id,
                'url': self.scraper.driver.current_url,
                'validation_type': 'valid'
            }
            
        except Exception as e:
            print(f"❌ Error validating VC page for {vc_id}: {e}")
            # On error, assume valid to continue with scraping
            return {
                'status': 'valid',
                'reason': f'Validation error: {e}',
                'vc_id': vc_id,
                'url': self.scraper.driver.current_url,
                'validation_type': 'error'
            }
