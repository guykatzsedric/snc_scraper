"""
State Manager for SNC Scraper
Handles loading and saving scraper state, VC status tracking, and resume functionality
"""
import os
import json

# Step 3: Import experimental resume detector (optional)
try:
    from .enhanced_resume_detector import EnhancedResumeDetector
except ImportError:
    EnhancedResumeDetector = None


class StateManager:
    def __init__(self, scraper_instance):
        """Initialize state manager with reference to scraper instance"""
        self.scraper = scraper_instance
    
    def load_previous_state(self):
        """
        Smart page-based state loading: Find which page to work on next
        Returns the target page number to process
        """
        try:
            target_page = 1  # Default if no previous pages found
            completed_pages = []
            in_progress_page = None
            
            # Scan results directory for page JSON files
            if os.path.exists(self.scraper.results_dir):
                for filename in os.listdir(self.scraper.results_dir):
                    if filename.startswith('page_') and filename.endswith('.json'):
                        filepath = os.path.join(self.scraper.results_dir, filename)
                        
                        try:
                            with open(filepath, 'r') as f:
                                page_data = json.load(f)
                            
                            # Get status and page number from metadata
                            if 'metadata' in page_data:
                                metadata = page_data['metadata']
                                page_num = metadata.get('page_number')
                                status = metadata.get('status')
                                total_vcs = metadata.get('total_vcs', 0)
                                
                                if status == 'in_progress':
                                    in_progress_page = page_num
                                    print(f"📋 Found in-progress page: {page_num} ({total_vcs} VCs)")
                                elif status == 'completed':
                                    completed_pages.append(page_num)
                                    print(f"✅ Completed page: {page_num} ({total_vcs} VCs)")
                            
                        except json.JSONDecodeError:
                            print(f"⚠️  Skipping corrupted file: {filename}")
                            continue
            
            # Determine target page using smart logic
            if in_progress_page is not None:
                # Continue the in-progress page
                target_page = in_progress_page
                print(f"🎯 Resuming in-progress page: {target_page}")
            elif completed_pages:
                # Start next page after highest completed
                target_page = max(completed_pages) + 1
                print(f"🎯 Starting new page: {target_page} (after {len(completed_pages)} completed pages)")
            else:
                # No previous pages, start from page 1
                target_page = 1
                print("🎯 Starting fresh from page 1")
            
            # Store target page in scraper for other methods to use
            self.scraper.target_page = target_page
            
            return target_page

        except Exception as e:
            print(f"❌ Error loading previous state: {e}")
            # Default to page 1 on error
            self.scraper.target_page = 1
            return 1
    
    # ======================================================
    # STEP 3: EXPERIMENTAL RESUME ENHANCEMENT (OPTIONAL)
    # ======================================================
    
    def load_previous_state_experimental(self, enable_experimental=False):
        """
        EXPERIMENTAL: Enhanced resume detection with cache integration
        
        Args:
            enable_experimental: Enable experimental resume logic (default: False)
            
        Returns:
            Page number to resume from
        """
        if not enable_experimental or EnhancedResumeDetector is None:
            print("💡 Using existing resume logic (experimental disabled)")
            return self.load_previous_state()  # Use existing logic
        
        try:
            print("🔬 EXPERIMENTAL: Enhanced resume detection enabled")
            
            # Initialize experimental resume detector
            experimental_detector = EnhancedResumeDetector(
                self.scraper, 
                enable_experimental=True
            )
            
            # Try experimental resume detection
            experimental_resume_point = experimental_detector.detect_resume_point_experimental()
            
            if experimental_resume_point is not None:
                print(f"✅ EXPERIMENTAL resume successful: page {experimental_resume_point}")
                self.scraper.target_page = experimental_resume_point
                return experimental_resume_point
            else:
                print("🔄 EXPERIMENTAL resume failed - falling back to existing logic")
                return self.load_previous_state()  # Fallback to existing
                
        except Exception as e:
            print(f"❌ EXPERIMENTAL resume error: {e}")
            print("🔄 Falling back to existing resume logic")
            return self.load_previous_state()  # Fallback to existing
    
    def get_resume_mode_status(self):
        """Get status of available resume modes"""
        return {
            "existing_resume": True,
            "experimental_resume": EnhancedResumeDetector is not None,
            "experimental_available": EnhancedResumeDetector is not None
        }