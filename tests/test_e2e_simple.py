#!/usr/bin/env python3
"""
End-to-End Test for SNC Scraper
Tests the complete scraper flow without manual login to verify all imports and functionality work correctly
Strategy: Mock login verification while using real browser + real website for integration testing
"""

import os
import sys
import json
import time
from unittest.mock import patch

print("🧪 Starting E2E Test for SNC Scraper...")
print("=" * 60)

# Test configuration - optimized for fast testing
TEST_CONFIG = {
    "verbose": True,
    "use_config": False,  # Use test config instead of user_config
    "test_vcs_limit": 2,  # Only test 2 VCs for speed
    "disable_delays": True,  # Disable human delays for testing
    "test_page": 1  # Test page 1
}

def create_test_scraper():
    """Create a scraper instance optimized for testing"""
    print("1️⃣ Creating test scraper instance...")
    
    try:
        from snc_scraper_service import SNCVCScraper
        
        # Create scraper without user config to avoid complex setup
        scraper = SNCVCScraper(
            verbose=TEST_CONFIG["verbose"], 
            use_config=TEST_CONFIG["use_config"]
        )
        
        print("   ✅ Scraper created successfully")
        return scraper
    except Exception as e:
        print(f"   ❌ Failed to create scraper: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_test_session_manager(scraper):
    """Create session manager for testing"""
    print("2️⃣ Creating session manager...")
    
    try:
        from helpers.session_manager import SessionManager
        
        session_manager = SessionManager(scraper)
        print("   ✅ SessionManager created successfully")
        return session_manager
    except Exception as e:
        print(f"   ❌ Failed to create session manager: {e}")
        import traceback
        traceback.print_exc()
        return None

def start_test_browser_session(session_manager):
    """Start browser session with auto-login bypass"""
    print("3️⃣ Starting browser session...")
    
    try:
        # Patch the manual login parts to auto-continue
        with patch.object(session_manager, 'verify_login', return_value=True):
            with patch('builtins.input', return_value=''):  # Auto-continue on input prompts
                
                # Start session but bypass manual login
                print("   🌐 Opening browser to SNC website...")
                from helpers.driver_factory import create_stealth_driver
                
                # Create browser driver
                session_manager.scraper.driver = create_stealth_driver(
                    proxy=None,  # No proxy for testing
                    user_agent=None,  # Auto user agent
                    headless=False  # Keep visible for debugging
                )
                
                # Navigate to the website
                session_manager.scraper.driver.get("https://finder.startupnationcentral.org")
                time.sleep(3)  # Wait for page load
                
                print("   ✅ Browser session started")
                print(f"   🔍 Current URL: {session_manager.scraper.driver.current_url}")
                
                return True
                
    except Exception as e:
        print(f"   ❌ Failed to start browser session: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_page_navigation(scraper):
    """Test navigation to a specific page"""
    print("4️⃣ Testing page navigation...")
    
    try:
        # Navigate to page 1 directly
        page_url = f"https://finder.startupnationcentral.org/vc/page/{TEST_CONFIG['test_page']}"
        print(f"   🔗 Navigating to: {page_url}")
        
        scraper.driver.get(page_url)
        time.sleep(5)  # Wait for page load
        
        # Check if we're on the right page
        current_url = scraper.driver.current_url
        print(f"   🔍 Current URL: {current_url}")
        
        # Check for VC elements on the page
        from selenium.webdriver.common.by import By
        vc_links = scraper.driver.find_elements(By.XPATH, "//a[contains(@href, '/vc/')]")
        print(f"   📋 Found {len(vc_links)} VC links on page")
        
        if len(vc_links) > 0:
            print("   ✅ Page navigation successful")
            return vc_links[:TEST_CONFIG["test_vcs_limit"]]  # Return limited VCs for testing
        else:
            print("   ⚠️  No VC links found - might need login")
            return []
            
    except Exception as e:
        print(f"   ❌ Failed page navigation: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_vc_scraping(scraper, vc_elements):
    """Test scraping individual VCs"""
    print("5️⃣ Testing VC scraping...")
    
    if not vc_elements:
        print("   ⚠️  No VCs to test")
        return []
    
    results = []
    
    try:
        from helpers.vc_page_helper.vc_orchestrator import VCOrchestrator
        vc_orchestrator = VCOrchestrator(scraper)
        
        # Test first VC only for speed
        for i, vc_element in enumerate(vc_elements[:TEST_CONFIG["test_vcs_limit"]]):
            print(f"   📊 Testing VC {i+1}/{len(vc_elements[:TEST_CONFIG['test_vcs_limit']])}")
            
            try:
                # Get VC URL
                vc_url = vc_element.get_attribute("href")
                if not vc_url or "/vc/" not in vc_url:
                    print(f"      ⚠️  Invalid VC URL: {vc_url}")
                    continue
                
                print(f"      🔗 Testing VC: {vc_url.split('/')[-1]}")
                
                # Test complete VC scraping (Overview + Investments)
                vc_data = vc_orchestrator.scrape_investor_complete_with_investments(vc_url)
                
                if vc_data:
                    print(f"      ✅ Successfully scraped: {vc_data.get('name', 'Unknown')}")
                    results.append(vc_data)
                else:
                    print(f"      ❌ Failed to scrape VC")
                    
            except Exception as e:
                print(f"      ❌ Error scraping VC {i+1}: {e}")
                continue
        
        print(f"   📈 Scraping results: {len(results)}/{len(vc_elements[:TEST_CONFIG['test_vcs_limit']])} successful")
        return results
        
    except Exception as e:
        print(f"   ❌ Failed VC scraping setup: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_data_saving(scraper, results):
    """Test data saving functionality"""
    print("6️⃣ Testing data saving...")
    
    try:
        if not results:
            print("   ⚠️  No results to save")
            return False
        
        # Test progress saving
        page_num = TEST_CONFIG["test_page"]
        scraper.save_page_progress(results, page_num)
        print(f"   ✅ Page progress saved: {len(results)} VCs")
        
        # Test final results saving
        final_path = scraper.save_final_results(results, "e2e_test")
        if final_path:
            print(f"   ✅ Final results saved: {final_path}")
            return True
        else:
            print("   ❌ Failed to save final results")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed data saving: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_helper_components(scraper):
    """Test individual helper components"""
    print("7️⃣ Testing helper components...")
    
    try:
        # Test VCOrchestrator
        from helpers.vc_page_helper.vc_orchestrator import VCOrchestrator
        vc_orchestrator = VCOrchestrator(scraper)
        print("   ✅ VCOrchestrator created")
        
        # Test overview scraper
        from helpers.vc_page_helper.overview_scraper import OverviewScraper
        overview_scraper = OverviewScraper(scraper)
        print("   ✅ OverviewScraper created")
        
        # Test investment scraper
        from helpers.vc_page_helper.investment_scraper import InvestmentScraper
        investment_scraper = InvestmentScraper(scraper)
        print("   ✅ InvestmentScraper created")
        
        # Test URL slug extraction
        test_url = "https://finder.startupnationcentral.org/vc/test-vc?utm_source=test"
        if hasattr(vc_orchestrator, 'extract_vc_slug'):
            slug = vc_orchestrator.extract_vc_slug(test_url)
            expected = "test-vc"
            if slug == expected:
                print("   ✅ URL slug extraction works")
            else:
                print(f"   ⚠️  URL slug extraction issue: got '{slug}', expected '{expected}'")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Helper components test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_browser(scraper):
    """Clean up browser session"""
    print("8️⃣ Cleaning up...")
    
    try:
        if scraper and scraper.driver:
            scraper.driver.quit()
            print("   ✅ Browser closed")
        else:
            print("   ℹ️  No browser to close")
    except Exception as e:
        print(f"   ⚠️  Error closing browser: {e}")

def main():
    """Run the complete E2E test"""
    print("🚀 SNC Scraper End-to-End Test")
    print("=" * 60)
    print(f"🔧 Test Configuration:")
    print(f"   • Test VCs limit: {TEST_CONFIG['test_vcs_limit']}")
    print(f"   • Test page: {TEST_CONFIG['test_page']}")
    print(f"   • Verbose mode: {TEST_CONFIG['verbose']}")
    print("=" * 60)
    
    scraper = None
    results = []
    test_results = {}
    
    try:
        # 1. Create scraper
        scraper = create_test_scraper()
        test_results["scraper_creation"] = scraper is not None
        
        if not scraper:
            print("❌ Cannot continue without scraper")
            return False
        
        # 2. Create session manager
        session_manager = create_test_session_manager(scraper)
        test_results["session_manager"] = session_manager is not None
        
        if not session_manager:
            print("❌ Cannot continue without session manager")
            return False
        
        # 3. Start browser session
        browser_started = start_test_browser_session(session_manager)
        test_results["browser_session"] = browser_started
        
        if not browser_started:
            print("❌ Cannot continue without browser")
            return False
        
        # 4. Test page navigation
        vc_elements = test_page_navigation(scraper)
        test_results["page_navigation"] = len(vc_elements) > 0
        
        # 5. Test VC scraping (if VCs found)
        if vc_elements:
            results = test_vc_scraping(scraper, vc_elements)
            test_results["vc_scraping"] = len(results) > 0
        else:
            print("⚠️  Skipping VC scraping - no VCs found")
            test_results["vc_scraping"] = False
        
        # 6. Test data saving
        if results:
            saving_success = test_data_saving(scraper, results)
            test_results["data_saving"] = saving_success
        else:
            print("⚠️  Skipping data saving - no results")
            test_results["data_saving"] = False
        
        # 7. Test helper components
        helpers_success = test_helper_components(scraper)
        test_results["helper_components"] = helpers_success
        
        # Print results summary
        print("\n" + "=" * 60)
        print("📋 E2E TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title():<20} {status}")
            if result:
                passed += 1
        
        print("=" * 60)
        print(f"Total: {passed}/{total} tests passed")
        
        if results:
            print(f"📊 Scraped {len(results)} VCs successfully:")
            for vc in results:
                print(f"   • {vc.get('name', 'Unknown')} ({vc.get('url', 'No URL')})")
        
        if passed == total:
            print("🎉 ALL TESTS PASSED! SNC Scraper is working correctly.")
            print("💡 Ready for manual login testing with real usage")
            return True
        else:
            print("⚠️  Some tests failed. Check issues above.")
            return False
            
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        return False
        
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Always cleanup
        cleanup_browser(scraper)

if __name__ == "__main__":
    success = main()
    print(f"\n{'🎉 E2E Test PASSED' if success else '❌ E2E Test FAILED'}")
    sys.exit(0 if success else 1)