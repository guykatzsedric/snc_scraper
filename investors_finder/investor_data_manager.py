#!/usr/bin/env python3
"""
Investor Data Manager for SNC Scraper
Manages investor database JSON with scraping status tracking
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional


class InvestorDataManager:
    """Manages investor database with scraping status and batch selection"""
    
    def __init__(self, database_path: str = "investor_database.json"):
        """
        Initialize investor data manager
        
        Args:
            database_path: Path to investor database JSON file
        """
        self.database_path = database_path
        self.investors_data = {}
        self.load_database()
    
    def load_database(self) -> bool:
        """
        Load investor database from JSON file
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.database_path):
                print(f"❌ Database file not found: {self.database_path}")
                return False
                
            with open(self.database_path, 'r', encoding='utf-8') as f:
                self.investors_data = json.load(f)
            
            print(f"✅ Loaded investor database: {len(self.investors_data)} investors")
            return True
            
        except Exception as e:
            print(f"❌ Error loading database: {e}")
            return False
    
    def save_database(self) -> bool:
        """
        Save investor database to JSON file
        
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.investors_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved investor database: {len(self.investors_data)} investors")
            return True
            
        except Exception as e:
            print(f"❌ Error saving database: {e}")
            return False
    
    def get_unscraped_investors(self, limit: int = 50) -> List[Dict]:
        """
        Get list of unscraped investors up to specified limit
        
        Args:
            limit: Maximum number of investors to return
            
        Returns:
            List of investor dictionaries ready for scraping
        """
        unscraped_investors = []
        
        for vc_id, vc_data in self.investors_data.items():
            # Check if investor needs scraping
            if self._needs_scraping(vc_data):
                # Prepare investor data for scraping
                investor_info = {
                    'vc_id': vc_id,
                    'name': vc_data.get('name', ''),
                    'url': vc_data.get('url', ''),
                    'type': vc_data.get('type', ''),
                    'managed_assets': vc_data.get('managed_assets', ''),
                    'investments': vc_data.get('investments', ''),
                    'investment_range': vc_data.get('investment_range', '')
                }
                unscraped_investors.append(investor_info)
                
                # Stop when we reach the limit
                if len(unscraped_investors) >= limit:
                    break
        
        print(f"🎯 Found {len(unscraped_investors)} unscraped investors (limit: {limit})")
        return unscraped_investors
    
    def _needs_scraping(self, vc_data: Dict) -> bool:
        """
        Determine if an investor needs scraping based on status
        
        Args:
            vc_data: Investor data dictionary
            
        Returns:
            bool: True if investor needs scraping
        """
        scraping_status = vc_data.get('scraping_status', 'not_scraped')
        
        # Investors that need scraping:
        # - never scraped
        # - failed scraping
        # - no scraping status set
        # 
        # Investors that DON'T need scraping:
        # - completed (already scraped successfully)
        # - inactive (PRESUMED INACTIVE)
        # - limited_info (limited information profile)
        return scraping_status in ['not_scraped', 'failed', None, '']
    
    def mark_investor_as_scraped(self, vc_id: str, scraped_data: Optional[Dict] = None) -> bool:
        """
        Mark investor as successfully scraped
        
        Args:
            vc_id: Investor ID
            scraped_data: Optional scraped data to merge
            
        Returns:
            bool: True if marked successfully
        """
        if vc_id not in self.investors_data:
            print(f"❌ Investor {vc_id} not found in database")
            return False
        
        try:
            # Update scraping status
            self.investors_data[vc_id]['scraping_status'] = 'completed'
            self.investors_data[vc_id]['last_scraped'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.investors_data[vc_id]['scraped_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Merge any additional scraped data
            if scraped_data:
                self.investors_data[vc_id].update(scraped_data)
            
            print(f"✅ Marked {vc_id} as scraped")
            return True
            
        except Exception as e:
            print(f"❌ Error marking {vc_id} as scraped: {e}")
            return False
    
    def mark_investor_as_failed(self, vc_id: str, error_message: Optional[str] = None) -> bool:
        """
        Mark investor as failed during scraping
        
        Args:
            vc_id: Investor ID
            error_message: Optional error message
            
        Returns:
            bool: True if marked successfully
        """
        if vc_id not in self.investors_data:
            print(f"❌ Investor {vc_id} not found in database")
            return False
        
        try:
            # Update scraping status
            self.investors_data[vc_id]['scraping_status'] = 'failed'
            self.investors_data[vc_id]['last_attempt'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if error_message:
                self.investors_data[vc_id]['last_error'] = error_message
            
            print(f"❌ Marked {vc_id} as failed")
            return True
            
        except Exception as e:
            print(f"❌ Error marking {vc_id} as failed: {e}")
            return False
    
    def mark_investor_as_inactive(self, vc_id: str) -> bool:
        """
        Mark investor as inactive (PRESUMED INACTIVE)
        
        Args:
            vc_id: Investor ID
            
        Returns:
            bool: True if marked successfully
        """
        if vc_id not in self.investors_data:
            print(f"❌ Investor {vc_id} not found in database")
            return False
        
        try:
            # Update scraping status
            self.investors_data[vc_id]['scraping_status'] = 'inactive'
            self.investors_data[vc_id]['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.investors_data[vc_id]['inactive_reason'] = 'PRESUMED INACTIVE No recent investments in Israel'
            
            print(f"⚠️ Marked {vc_id} as inactive")
            return True
            
        except Exception as e:
            print(f"❌ Error marking {vc_id} as inactive: {e}")
            return False
    
    def mark_investor_as_limited(self, vc_id: str) -> bool:
        """
        Mark investor as having limited information
        
        Args:
            vc_id: Investor ID
            
        Returns:
            bool: True if marked successfully
        """
        if vc_id not in self.investors_data:
            print(f"❌ Investor {vc_id} not found in database")
            return False
        
        try:
            # Update scraping status
            self.investors_data[vc_id]['scraping_status'] = 'limited_info'
            self.investors_data[vc_id]['last_checked'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.investors_data[vc_id]['limited_reason'] = 'This profile has limited information'
            
            print(f"ℹ️ Marked {vc_id} as limited_info")
            return True
            
        except Exception as e:
            print(f"❌ Error marking {vc_id} as limited_info: {e}")
            return False
    
    def get_scraping_stats(self) -> Dict:
        """
        Get statistics about scraping progress
        
        Returns:
            Dictionary with scraping statistics
        """
        stats = {
            'total_investors': len(self.investors_data),
            'completed': 0,
            'failed': 0,
            'inactive': 0,
            'limited_info': 0,
            'not_scraped': 0,
            'completion_percentage': 0.0
        }
        
        for vc_data in self.investors_data.values():
            status = vc_data.get('scraping_status', 'not_scraped')
            
            if status == 'completed':
                stats['completed'] += 1
            elif status == 'failed':
                stats['failed'] += 1
            elif status == 'inactive':
                stats['inactive'] += 1
            elif status == 'limited_info':
                stats['limited_info'] += 1
            else:
                stats['not_scraped'] += 1
        
        # Calculate completion percentage (completed out of scrapeable VCs)
        scrapeable_vcs = stats['total_investors'] - stats['inactive'] - stats['limited_info']
        if scrapeable_vcs > 0:
            stats['completion_percentage'] = (stats['completed'] / scrapeable_vcs) * 100
        
        return stats
    
    def print_stats(self):
        """Print current scraping statistics"""
        stats = self.get_scraping_stats()
        
        print(f"\n📊 === INVESTOR SCRAPING STATISTICS ===")
        print(f"Total Investors: {stats['total_investors']}")
        print(f"✅ Completed: {stats['completed']}")
        print(f"❌ Failed: {stats['failed']}")
        print(f"⚠️ Inactive: {stats['inactive']}")
        print(f"ℹ️ Limited Info: {stats['limited_info']}")
        print(f"⏳ Not Scraped: {stats['not_scraped']}")
        print(f"📈 Completion: {stats['completion_percentage']:.1f}% (of scrapeable VCs)")
        print(f"📊 =====================================")


def test_investor_data_manager():
    """Test function for InvestorDataManager"""
    print("🧪 Testing InvestorDataManager...")
    
    # Initialize manager
    manager = InvestorDataManager()
    
    # Print initial stats
    manager.print_stats()
    
    # Get 5 unscraped investors for testing
    test_investors = manager.get_unscraped_investors(limit=5)
    
    if test_investors:
        print(f"\n🎯 Sample unscraped investors:")
        for i, investor in enumerate(test_investors[:3], 1):
            print(f"  {i}. {investor['name']} ({investor['vc_id']})")
            print(f"     URL: {investor['url']}")
    
    print("\n✅ InvestorDataManager test completed")


if __name__ == "__main__":
    test_investor_data_manager()