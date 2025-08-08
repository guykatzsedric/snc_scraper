"""
VC Cache Manager for SNC Scraper
Provides standalone VC tracking functionality with zero impact on existing system.

Step 1: Basic cache operations only - no integration yet.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class VCCacheManager:
    """Manages a persistent cache of VC information for tracking scraping progress"""
    
    def __init__(self, cache_file_path: str = None):
        """Initialize cache manager with specified cache file path"""
        if cache_file_path is None:
            # Default to cache file in the SNC scraper directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            snc_dir = os.path.dirname(current_dir)  # Go up one level to snc directory
            cache_file_path = os.path.join(snc_dir, "vc_cache.json")
        
        self.cache_file_path = cache_file_path
        self.cache_data = {}
        self._load_cache()
    
    def _load_cache(self) -> None:
        """Load cache from file, create empty cache if file doesn't exist"""
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    self.cache_data = json.load(f)
                print(f"✅ Loaded VC cache: {len(self.cache_data)} VCs from {self.cache_file_path}")
            else:
                self.cache_data = {}
                print(f"📁 Created new VC cache at {self.cache_file_path}")
        except Exception as e:
            print(f"⚠️ Error loading VC cache: {e}")
            self.cache_data = {}
    
    def _save_cache(self) -> bool:
        """Save cache to file"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
            
            # Save with pretty formatting
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving VC cache: {e}")
            return False
    
    def add_vc(self, slug: str, name: str, url: str, first_seen_page: int = None) -> bool:
        """Add a new VC to the cache"""
        try:
            self.cache_data[slug] = {
                "name": name,
                "url": url,
                "slug": slug,
                "first_seen_page": first_seen_page,
                "scraping_status": "pending",
                "first_discovered": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "last_scraped": None,
                "scrape_attempts": 0,
                "data_hash": None
            }
            return self._save_cache()
        except Exception as e:
            print(f"❌ Error adding VC {slug}: {e}")
            return False
    
    def get_vc_status(self, slug: str) -> Optional[str]:
        """Get the scraping status of a VC"""
        return self.cache_data.get(slug, {}).get("scraping_status")
    
    def mark_vc_completed(self, slug: str, data_hash: str = None) -> bool:
        """Mark a VC as successfully scraped"""
        try:
            if slug in self.cache_data:
                self.cache_data[slug]["scraping_status"] = "completed"
                self.cache_data[slug]["last_scraped"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cache_data[slug]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if data_hash:
                    self.cache_data[slug]["data_hash"] = data_hash
                return self._save_cache()
            return False
        except Exception as e:
            print(f"❌ Error marking VC {slug} as completed: {e}")
            return False
    
    def mark_vc_failed(self, slug: str) -> bool:
        """Mark a VC as failed to scrape"""
        try:
            if slug in self.cache_data:
                self.cache_data[slug]["scraping_status"] = "failed"
                self.cache_data[slug]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cache_data[slug]["scrape_attempts"] += 1
                return self._save_cache()
            return False
        except Exception as e:
            print(f"❌ Error marking VC {slug} as failed: {e}")
            return False
    
    def get_pending_vcs(self) -> List[Dict]:
        """Get list of VCs that need to be scraped"""
        return [
            data for slug, data in self.cache_data.items() 
            if data.get("scraping_status") == "pending"
        ]
    
    def get_completed_vcs(self) -> List[Dict]:
        """Get list of successfully scraped VCs"""
        return [
            data for slug, data in self.cache_data.items() 
            if data.get("scraping_status") == "completed"
        ]
    
    def get_failed_vcs(self) -> List[Dict]:
        """Get list of VCs that failed to scrape"""
        return [
            data for slug, data in self.cache_data.items() 
            if data.get("scraping_status") == "failed"
        ]
    
    def is_vc_completed(self, slug: str) -> bool:
        """Check if a VC has been successfully scraped"""
        return self.get_vc_status(slug) == "completed"
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache"""
        total = len(self.cache_data)
        completed = len(self.get_completed_vcs())
        pending = len(self.get_pending_vcs())
        failed = len(self.get_failed_vcs())
        
        return {
            "total_vcs": total,
            "completed": completed,
            "pending": pending,
            "failed": failed,
            "completion_rate": f"{(completed/total*100):.1f}%" if total > 0 else "0%"
        }
    
    def print_cache_stats(self) -> None:
        """Print cache statistics"""
        stats = self.get_cache_stats()
        print("📊 VC Cache Statistics:")
        print(f"   Total VCs: {stats['total_vcs']}")
        print(f"   ✅ Completed: {stats['completed']}")
        print(f"   ⏳ Pending: {stats['pending']}")
        print(f"   ❌ Failed: {stats['failed']}")
        print(f"   📈 Completion Rate: {stats['completion_rate']}")


def test_vc_cache_manager():
    """Standalone test function for the VC cache manager"""
    print("🧪 Testing VC Cache Manager...")
    
    # Create test cache manager
    test_cache_path = "/tmp/test_vc_cache.json"
    cache_manager = VCCacheManager(test_cache_path)
    
    # Test adding VCs
    print("\n1️⃣ Testing VC addition...")
    success1 = cache_manager.add_vc(
        slug="test-vc-1",
        name="Test VC 1",
        url="https://example.com/test-vc-1",
        first_seen_page=1
    )
    success2 = cache_manager.add_vc(
        slug="test-vc-2", 
        name="Test VC 2",
        url="https://example.com/test-vc-2",
        first_seen_page=2
    )
    print(f"   Added VC 1: {'✅' if success1 else '❌'}")
    print(f"   Added VC 2: {'✅' if success2 else '❌'}")
    
    # Test status checking
    print("\n2️⃣ Testing status checking...")
    status1 = cache_manager.get_vc_status("test-vc-1")
    status2 = cache_manager.get_vc_status("non-existent-vc")
    print(f"   VC 1 status: {status1}")
    print(f"   Non-existent VC status: {status2}")
    
    # Test marking as completed
    print("\n3️⃣ Testing completion marking...")
    completed = cache_manager.mark_vc_completed("test-vc-1", "hash123")
    print(f"   Marked VC 1 as completed: {'✅' if completed else '❌'}")
    
    # Test statistics
    print("\n4️⃣ Testing statistics...")
    cache_manager.print_cache_stats()
    
    # Test getting lists
    print("\n5️⃣ Testing list retrieval...")
    pending = cache_manager.get_pending_vcs()
    completed_list = cache_manager.get_completed_vcs()
    print(f"   Pending VCs: {len(pending)}")
    print(f"   Completed VCs: {len(completed_list)}")
    
    # Cleanup
    try:
        os.remove(test_cache_path)
        print("\n🧹 Cleaned up test file")
    except:
        pass
    
    print("✅ VC Cache Manager test completed!")


if __name__ == "__main__":
    test_vc_cache_manager()