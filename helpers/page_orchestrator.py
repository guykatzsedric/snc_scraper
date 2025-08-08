"""
Page Orchestrator for SNC Scraper
Handles page-level coordination and processing logic
"""
from services.scrapers.snc.helpers.search_page_helper import SearchPageHelper


class PageOrchestrator:
    def __init__(self, scraper_instance):
        """Initialize page orchestrator with reference to scraper instance"""
        self.scraper = scraper_instance
    
    def scrape_pages(self, start_page=None, end_page=None, max_tabs=7, resume_from_vc=0):
        """Page-based scraping with intelligent auto-resume functionality"""
        all_results = []
        page_num = start_page
        self.scraper.current_page = page_num

        # Process pages until end_page or no more pages
        while True:
            print(f"\n📄 ===== PROCESSING PAGE {page_num} =====")
            self.scraper.current_page = page_num

            # Reset rate limit flag for new page
            self.scraper.rate_limit_detected = False

            # Navigate directly to this page using URL
            search_page_helper = SearchPageHelper(self.scraper)
            if not search_page_helper.navigate_to_page(page_num):
                print(f"❌ Could not navigate to page {page_num}")
                if page_num == start_page:
                    print("❌ Failed to load starting page - aborting")
                    break
                else:
                    print("⚠️  Reached end of available pages")
                    break

            # Process this single page
            page_results, actual_page = self.process_single_page(page_num, max_tabs)

            if page_results:
                all_results.extend(page_results)
                print(f"✅ Page {page_num} completed: {len(page_results)} VCs")
            else:
                print(f"⚠️  Page {page_num} returned no results")

            # Stop conditions
            if end_page and page_num >= end_page:
                print(f"✅ Reached target end page {end_page}")
                break

            if self.scraper.rate_limit_detected:
                print("🚨 Rate limit detected - stopping gracefully")
                break

            if not page_results:  # No results from page
                print("⚠️  No results from page - likely reached end")
                break

            # Move to next page
            page_num += 1

            # Safety check: don't go beyond reasonable page limit
            if page_num > 50:
                print("⚠️  Reached safety limit of 50 pages")
                break

        print(f"\n🎉 PAGES COMPLETE: {len(all_results)} total VCs scraped")
        return all_results, page_num - 1

    def process_single_page(self, page_num=None, max_tabs=7):
        """Process single page with state management and progressive saving"""
        if page_num is None:
            page_num = self.scraper.current_page

        print(f"\n🏁 === SCRAPING PAGE {page_num} ===")
        print(f"🔍 DEBUG: Starting enhanced single page scraping...")
        print(f"🔍 DEBUG: Max tabs: {max_tabs}")
        print(f"🔍 DEBUG: User type: {self.scraper.user_type}")
        print(f"🔍 DEBUG: Looking in results directory for existing files...")


        # Step 3: Load existing progress for this page
        existing_vcs, existing_status, _ = self.scraper.load_page_with_enhanced_metadata(page_num)
        if existing_vcs:
            print(f"📁 Found existing data: {len(existing_vcs)} VCs, status: {existing_status}")

            # Check if page is already completed
            if existing_status == "completed":
                print(f"✅ Page {page_num} already completed - returning existing data")
                return existing_vcs, page_num

            # Page exists but not completed - determine what to scrape
            search_page_helper = SearchPageHelper(self.scraper)
            all_vc_links = search_page_helper.extract_vc_links_from_search_page()

            if not all_vc_links:
                print(f"❌ No VCs found on page {page_num}")
                return [], page_num

            # Filter VCs that still need scraping
            vcs_to_scrape = search_page_helper.filter_unscraped_vcs(all_vc_links, existing_vcs)

            if not vcs_to_scrape:
                print(f"✅ All VCs on page {page_num} already scraped - marking as completed")
                self.scraper.save_page_with_enhanced_metadata(page_num, existing_vcs, "completed")
                return existing_vcs, page_num

            print(f"🔄 Resuming page {page_num}: {len(vcs_to_scrape)} VCs remaining")

        else:
            # No existing data - start fresh
            print(f"🆕 Starting fresh page {page_num}")

            # Extract all VC links from this page
            search_page_helper = SearchPageHelper(self.scraper)
            all_vc_links = search_page_helper.extract_vc_links_from_search_page()

            if not all_vc_links:
                print(f"❌ No VCs found on page {page_num}")
                return [], page_num

            vcs_to_scrape = all_vc_links
            existing_vcs = []

        print(f"🎯 Target: {len(vcs_to_scrape)} VCs to scrape on page {page_num}")

        # Step 4: Scrape VCs using parallel tabs
        if vcs_to_scrape:
            print(f"🚀 Starting parallel scraping: {len(vcs_to_scrape)} VCs with {max_tabs} tabs")
            new_results = self.scraper.scrape_vcs_in_parallel_tabs(vcs_to_scrape, max_tabs=max_tabs, page_num=page_num)
            print(f"✅ Parallel scraping completed: {len(new_results)} successful")
        else:
            new_results = []

        # Step 5: Combine results (existing + new)
        all_page_results = existing_vcs + new_results
        print(f"📊 Total page results: {len(all_page_results)} VCs")

        # Step 6: Save progress with enhanced metadata
        final_status = "completed"  # Mark as completed
        self.scraper.save_page_with_enhanced_metadata(page_num, all_page_results, final_status)

        # Save page completion progress
        self.scraper.save_page_progress(all_page_results, page_num)

        print(f"📏 Page {page_num} completed and saved")
        print(f"   📄 {len(all_page_results)} VCs from ACTUAL page {page_num}")
        print(f"   💼 User: {self.scraper.user_type}")

        return all_page_results, page_num