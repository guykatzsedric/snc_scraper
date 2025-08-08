#!/usr/bin/env python3
"""
Direct Investor Scraper for SNC (Standalone Version)
Uses existing components from snc_scraper_service.py with new investor database approach
"""

import os
import json
import sys
from datetime import datetime

# Add project root to Python path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import existing SNC scraper components (reuse everything!)
from services.scrapers.snc.snc_scraper_service import SNCVCScraper
from services.scrapers.snc.helpers.session_manager import SessionManager

# Import new investor data manager
from services.scrapers.snc.investors_finder.investor_data_manager import InvestorDataManager


def run_direct_investor_session():
    """
    Direct investor scraping session - replaces page-based approach
    Uses existing components with investor database approach
    """
    print("🎯 SNC SCRAPER - DIRECT INVESTOR SESSION")
    print("=" * 50)

    # Create scraper with user configuration (same as existing)
    scraper = SNCVCScraper(verbose=True, use_config=True)
    
    # Create session manager (same as existing)
    session_manager = SessionManager(scraper)
    
    # NEW: Create investor data manager
    investor_manager = InvestorDataManager(database_path='/Users/entree/PycharmProjects/chef-pipeline/chief_os/services/scrapers/snc/investors_finder/investor_database.json')

    try:
        print("\n1️⃣ Starting session and login...")
        session_manager.start_session()
        
        # NEW APPROACH: Get 50 VCs from investor database instead of page navigation
        print("\n2️⃣ Getting investors to scrape from database...")
        investors_to_scrape = investor_manager.get_unscraped_investors(limit=50)
        
        if not investors_to_scrape:
            print("⚠️  No unscraped investors found - all may be completed!")
            investor_manager.print_stats()
            return
        
        print(f"🎯 Selected {len(investors_to_scrape)} investors for scraping")
        
        # Convert investor data to URLs for existing scraping method
        vc_urls = [investor['url'] for investor in investors_to_scrape]
        print(f"📋 URLs ready: {len(vc_urls)} VCs")
        
        print("\n3️⃣ Scraping investors using existing parallel tabs method...")
        # Use existing scrape_vcs_in_parallel_tabs method (no changes needed!)
        results = scraper.scrape_vcs_in_parallel_tabs(vc_urls, max_tabs=7, page_num=None)
        
        print(f"\n4️⃣ Processing results...")
        successful_vcs = []
        failed_vcs = []
        inactive_vcs = []
        limited_info_vcs = []
        
        # Process results and categorize them
        for result in results:
            if not result:
                continue
                
            vc_id = result.get('vc_id', '')
            if not vc_id:
                # Try to extract vc_id from URL if not present
                url = result.get('url', '')
                if url:
                    vc_id = url.split('/')[-1]
            
            # Check if this is a validation result (not full scraped data)
            if 'validation_type' in result:
                validation_status = result.get('status')
                if validation_status == 'inactive':
                    inactive_vcs.append(vc_id)
                    investor_manager.mark_investor_as_inactive(vc_id)
                    print(f"⚠️ {vc_id} - marked as inactive")
                elif validation_status == 'limited_info':
                    limited_info_vcs.append(vc_id)
                    investor_manager.mark_investor_as_limited(vc_id)
                    print(f"ℹ️ {vc_id} - marked as limited info")
            else:
                # This is full scraped data
                if vc_id and result.get('name'):  # Has actual scraped content
                    successful_vcs.append(vc_id)
                    investor_manager.mark_investor_as_scraped(vc_id)
                    print(f"✅ {vc_id} - scraped successfully")
                else:
                    failed_vcs.append(vc_id)
                    investor_manager.mark_investor_as_failed(vc_id, "Scraping failed")
                    print(f"❌ {vc_id} - failed to scrape")
        
        # Check for any investors that weren't processed at all
        processed_vc_ids = set(successful_vcs + failed_vcs + inactive_vcs + limited_info_vcs)
        for investor in investors_to_scrape:
            vc_id = investor['vc_id']
            if vc_id not in processed_vc_ids:
                failed_vcs.append(vc_id)
                investor_manager.mark_investor_as_failed(vc_id, "Not processed")
                print(f"❌ {vc_id} - not processed")
        
        print("\n5️⃣ Saving results...")
        # Filter results - only save actual scraped data, not validation results
        scraped_data_only = [result for result in results if result and 'validation_type' not in result]
        
        # Save results with new naming convention
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_filename = f"completed_{len(scraped_data_only)}_vcs_{timestamp}.json"
        
        # Use existing save method but with new filename and filtered data
        if scraped_data_only:
            scraper.save_final_results(scraped_data_only, f"direct_batch_{timestamp}")
            print(f"💾 Saved {len(scraped_data_only)} scraped VCs to results")
        else:
            print("💾 No scraped data to save (only validation results)")
        
        # Save updated investor database
        investor_manager.save_database()
        
        print(f"\n🎉 Direct investor session completed!")
        print(f"✅ Successfully scraped: {len(successful_vcs)} VCs")
        print(f"⚠️ Inactive VCs: {len(inactive_vcs)} VCs")
        print(f"ℹ️ Limited info VCs: {len(limited_info_vcs)} VCs") 
        print(f"❌ Failed: {len(failed_vcs)} VCs")
        print(f"💾 Only scraped data saved ({len([r for r in results if r and 'validation_type' not in r])} VCs)")
        
        # Print updated stats
        investor_manager.print_stats()

    except KeyboardInterrupt:
        print("\n⏹️  Session interrupted...")
        if 'investor_manager' in locals():
            investor_manager.save_database()

    except Exception as e:
        print(f"❌ Error during session: {e}")
        if 'investor_manager' in locals():
            investor_manager.save_database()

    finally:
        scraper.close_session()


if __name__ == "__main__":
    print("🎯 DIRECT INVESTOR SCRAPER (STANDALONE)")
    print("=" * 40)
    print()
    
    run_direct_investor_session()