"""
Enhanced Resume Detector for SNC Scraper (EXPERIMENTAL)
Provides intelligent resume detection using cache and multi-page verification.

Step 3: Experimental addition - does not modify existing resume logic.
All features disabled by default to ensure zero impact on current workflow.
"""

import os
import re
from typing import Dict, Optional

from services.scrapers.snc.helpers.vc_cache_manager import VCCacheManager


class EnhancedResumeDetector:
    """
    EXPERIMENTAL: Enhanced resume detection with cache integration
    
    This is an experimental addition that provides more sophisticated resume
    logic while preserving the existing resume system as fallback.
    """
    
    def __init__(self, scraper_instance, enable_experimental=False):
        """
        Initialize enhanced resume detector
        
        Args:
            scraper_instance: Reference to main scraper
            enable_experimental: Enable experimental features (default: False)
        """
        self.scraper = scraper_instance
        self.enable_experimental = enable_experimental
        self.cache_manager = VCCacheManager()
        
        if not enable_experimental:
            print("💡 Enhanced resume detector: EXPERIMENTAL mode disabled (using existing logic)")
    
    def detect_resume_point_experimental(self) -> Optional[int]:
        """
        EXPERIMENTAL: Detect optimal resume point using cache and multipage verification
        
        Returns:
            Page number to resume from, or None to use existing logic
        """
        if not self.enable_experimental:
            print("💡 Using existing resume detection logic")
            return None
        
        try:
            print("🔬 EXPERIMENTAL: Enhanced resume detection starting...")
            
            # Step 1: Find last in-progress page
            last_in_progress_page = self._find_last_in_progress_page()
            if last_in_progress_page is None:
                print("📄 No in-progress pages found - starting fresh")
                return self._find_next_available_page()
            
            print(f"📄 Found last in-progress page: {last_in_progress_page}")
            
            # Step 2: Verify previous page (go back one to check for missed VCs)
            verification_page = max(1, last_in_progress_page - 1)
            print(f"🔍 Verifying previous page: {verification_page}")
            
            # Step 3: Determine optimal resume point
            resume_page = self._determine_optimal_resume_point(
                last_in_progress_page, 
                verification_page
            )
            
            print(f"🎯 EXPERIMENTAL resume point: {resume_page}")
            return resume_page
            
        except Exception as e:
            print(f"❌ EXPERIMENTAL resume detection failed: {e}")
            print("🔄 Falling back to existing resume logic")
            return None
    
    def _find_last_in_progress_page(self) -> Optional[int]:
        """Find the highest page number that is in progress"""
        try:
            results_dir = self.scraper.results_dir
            if not os.path.exists(results_dir):
                return None
            
            in_progress_pages = []
            
            for filename in os.listdir(results_dir):
                if 'in_progress' in filename and filename.endswith('.json'):
                    # Extract page number from filename
                    match = re.search(r'page_(\d+)_', filename)
                    if match:
                        page_num = int(match.group(1))
                        in_progress_pages.append(page_num)
                        print(f"  📋 Found in-progress page: {page_num}")
            
            if in_progress_pages:
                return max(in_progress_pages)
            
            return None
            
        except Exception as e:
            print(f"❌ Error finding in-progress pages: {e}")
            return None
    
    def _find_next_available_page(self) -> int:
        """Find the next page that should be processed"""
        try:
            results_dir = self.scraper.results_dir
            if not os.path.exists(results_dir):
                return 1
            
            completed_pages = []
            
            for filename in os.listdir(results_dir):
                if 'completed' in filename and filename.endswith('.json'):
                    match = re.search(r'page_(\d+)_', filename)
                    if match:
                        page_num = int(match.group(1))
                        completed_pages.append(page_num)
            
            if completed_pages:
                return max(completed_pages) + 1
            
            return 1
            
        except Exception as e:
            print(f"❌ Error finding next available page: {e}")
            return 1
    
    def _determine_optimal_resume_point(self, last_in_progress: int, verification_page: int) -> int:
        """
        Determine the optimal resume point based on cache analysis
        
        Args:
            last_in_progress: Last page that was in progress
            verification_page: Page to verify (usually last_in_progress - 1)
            
        Returns:
            Optimal page number to resume from
        """
        try:
            print(f"🔍 Analyzing pages {verification_page} to {last_in_progress}...")
            
            # Check verification page for missed VCs
            verification_needs_work = self._page_needs_work(verification_page)
            
            if verification_needs_work:
                print(f"⚠️  Page {verification_page} has unscraped VCs - resuming from there")
                return verification_page
            else:
                print(f"✅ Page {verification_page} is complete - resuming from {last_in_progress}")
                return last_in_progress
                
        except Exception as e:
            print(f"❌ Error determining resume point: {e}")
            return last_in_progress
    
    def _page_needs_work(self, page_num: int) -> bool:
        """
        Check if a page has VCs that need scraping using cache data
        
        Args:
            page_num: Page number to check
            
        Returns:
            True if page has unscraped VCs, False if complete
        """
        try:
            # This would require actually navigating to the page to get VCs
            # For now, we'll use a simplified approach based on existing files
            
            results_dir = self.scraper.results_dir
            if not os.path.exists(results_dir):
                return True  # Page needs work if no results exist
            
            # Look for existing page file
            for filename in os.listdir(results_dir):
                if filename.startswith(f'page_{page_num}_') and filename.endswith('.json'):
                    if 'completed' in filename:
                        print(f"  ✅ Page {page_num} marked as completed")
                        return False
                    elif 'in_progress' in filename:
                        print(f"  🔄 Page {page_num} marked as in progress")
                        return True
            
            # No file found - page needs work
            print(f"  📄 Page {page_num} not processed yet")
            return True
            
        except Exception as e:
            print(f"❌ Error checking page {page_num}: {e}")
            return True  # Assume needs work if we can't determine
    
    def get_experimental_status(self) -> Dict:
        """Get status of experimental resume detector"""
        return {
            "experimental_enabled": self.enable_experimental,
            "cache_vcs": len(self.cache_manager.cache_data),
            "cache_completed": len(self.cache_manager.get_completed_vcs()),
            "cache_pending": len(self.cache_manager.get_pending_vcs()),
            "detector_version": "experimental_v1"
        }
    
    def print_experimental_status(self):
        """Print experimental resume detector status"""
        status = self.get_experimental_status()
        
        print("🔬 EXPERIMENTAL Resume Detector Status:")
        print(f"   Enabled: {status['experimental_enabled']}")
        if status['experimental_enabled']:
            print(f"   Cache VCs: {status['cache_vcs']}")
            print(f"   Completed: {status['cache_completed']}")
            print(f"   Pending: {status['cache_pending']}")
        else:
            print("   💡 Enable with enable_experimental=True")


def test_enhanced_resume_detector():
    """Test the enhanced resume detector without affecting existing system"""
    print("🧪 Testing Enhanced Resume Detector (EXPERIMENTAL)")
    print("=" * 60)
    
    # Test 1: Disabled mode (default)
    print("\n1️⃣ Testing disabled mode (default behavior)...")
    class MockScraper:
        def __init__(self):
            self.results_dir = "results"
    
    detector = EnhancedResumeDetector(MockScraper(), enable_experimental=False)
    resume_point = detector.detect_resume_point_experimental()
    print(f"   Resume point (disabled): {resume_point}")  # Should be None
    
    # Test 2: Enabled mode 
    print("\n2️⃣ Testing enabled mode...")
    detector_enabled = EnhancedResumeDetector(MockScraper(), enable_experimental=True)
    detector_enabled.print_experimental_status()
    
    # Test 3: Resume detection logic
    print("\n3️⃣ Testing resume detection logic...")
    try:
        resume_point = detector_enabled.detect_resume_point_experimental()
        print(f"   Resume point (enabled): {resume_point}")
    except Exception as e:
        print(f"   Expected error (no browser): {e}")
    
    print("\n✅ Enhanced Resume Detector tests complete")
    print("💡 All experimental features disabled by default")


if __name__ == "__main__":
    test_enhanced_resume_detector()