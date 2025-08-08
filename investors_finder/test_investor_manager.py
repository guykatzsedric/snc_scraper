#!/usr/bin/env python3
"""
Simple test for InvestorDataManager
Tests core functionality to ensure it works correctly
"""

from investor_data_manager import InvestorDataManager


def test_investor_manager():
    """Test core InvestorDataManager functionality"""
    print("🧪 Testing InvestorDataManager...")
    
    # Initialize manager
    manager = InvestorDataManager()
    print(f"✅ Loaded {len(manager.investors_data)} investors")
    
    # Test 1: Get 10 unscraped investors
    print("\n--- Test 1: Get unscraped investors ---")
    investors = manager.get_unscraped_investors(limit=10)
    print(f"Selected {len(investors)} investors")
    assert len(investors) == 10, "Should get exactly 10 investors"
    
    # Test 2: Mark some as scraped and failed
    print("\n--- Test 2: Update statuses ---")
    # Mark first 3 as scraped
    for i in range(3):
        vc_id = investors[i]['vc_id']
        manager.mark_investor_as_scraped(vc_id)
    
    # Mark next 2 as failed
    for i in range(3, 5):
        vc_id = investors[i]['vc_id']
        manager.mark_investor_as_failed(vc_id, "Test failure")
    
    # Check stats
    stats = manager.get_scraping_stats()
    print(f"Stats: {stats['completed']} completed, {stats['failed']} failed")
    assert stats['completed'] == 3, "Should have 3 completed"
    assert stats['failed'] == 2, "Should have 2 failed"
    
    # Test 3: Save and reload
    print("\n--- Test 3: Save and reload ---")
    manager.save_database()
    
    new_manager = InvestorDataManager()
    new_stats = new_manager.get_scraping_stats()
    print(f"After reload - Stats: {new_stats['completed']} completed, {new_stats['failed']} failed")
    assert new_stats['completed'] == 3, "Completed count should persist"
    assert new_stats['failed'] == 2, "Failed count should persist"
    
    # Test 4: Get new batch (should exclude completed but include failed for retry)
    print("\n--- Test 4: Get new batch (excluding completed VCs) ---")
    new_batch = new_manager.get_unscraped_investors(limit=10)
    print(f"New batch size: {len(new_batch)}")
    
    # Verify completed VCs are excluded but failed VCs are included (for retry)
    completed_vc_ids = {investors[i]['vc_id'] for i in range(3)}  # First 3 marked as completed
    failed_vc_ids = {investors[i]['vc_id'] for i in range(3, 5)}  # Next 2 marked as failed
    new_vc_ids = {inv['vc_id'] for inv in new_batch}
    
    completed_overlap = completed_vc_ids.intersection(new_vc_ids)
    failed_overlap = failed_vc_ids.intersection(new_vc_ids)
    
    print(f"Completed VCs in new batch: {len(completed_overlap)} (should be 0)")
    print(f"Failed VCs in new batch: {len(failed_overlap)} (should be 2 for retry)")
    
    assert len(completed_overlap) == 0, "No completed VCs should appear in new batch"
    assert len(failed_overlap) == 2, "Failed VCs should appear for retry"
    
    print("\n✅ All tests passed! InvestorDataManager is working correctly.")
    
    # Print final stats
    new_manager.print_stats()


if __name__ == "__main__":
    test_investor_manager()