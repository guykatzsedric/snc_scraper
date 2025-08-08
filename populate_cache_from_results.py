"""
Populate VC Cache from Existing Results
Standalone script to populate the VC cache with previously scraped VCs from /results/ directory.

Step 1.5: Cache population - no integration yet, just data migration.
"""

import json
import os
import re
from datetime import datetime
from helpers.vc_cache_manager import VCCacheManager


def extract_page_number_from_filename(filename):
    """Extract page number from result filename"""
    match = re.search(r'page_(\d+)_completed', filename)
    return int(match.group(1)) if match else None


def load_result_file(file_path):
    """Load and parse a result JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Error loading {file_path}: {e}")
        return None


def extract_vc_data_from_results(results_data, page_number, filename):
    """Extract VC information from results data"""
    vcs = []
    
    # Handle direct array format (like the files we saw)
    if isinstance(results_data, list):
        for vc_data in results_data:
            if isinstance(vc_data, dict) and 'vc_id' in vc_data:
                vc_info = {
                    'slug': vc_data['vc_id'],
                    'name': vc_data.get('name', 'Unknown'),
                    'url': vc_data.get('url', ''),
                    'page_number': page_number,
                    'scraped_at': vc_data.get('scraped_at', ''),
                    'source_file': filename
                }
                vcs.append(vc_info)
    
    # Handle metadata wrapper format (if any)
    elif isinstance(results_data, dict):
        if 'vcs' in results_data and isinstance(results_data['vcs'], list):
            for vc_data in results_data['vcs']:
                if isinstance(vc_data, dict) and 'vc_id' in vc_data:
                    vc_info = {
                        'slug': vc_data['vc_id'],
                        'name': vc_data.get('name', 'Unknown'),
                        'url': vc_data.get('url', ''),
                        'page_number': page_number,
                        'scraped_at': vc_data.get('scraped_at', ''),
                        'source_file': filename
                    }
                    vcs.append(vc_info)
    
    return vcs


def populate_cache_from_results():
    """Main function to populate cache from results directory"""
    print("🔄 Populating VC Cache from Results Directory...")
    print("=" * 60)
    
    # Initialize cache manager
    cache_manager = VCCacheManager()
    
    # Get current cache stats
    initial_stats = cache_manager.get_cache_stats()
    print(f"📊 Initial cache state: {initial_stats['total_vcs']} VCs")
    
    # Get results directory path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(current_dir, "results")
    
    if not os.path.exists(results_dir):
        print(f"❌ Results directory not found: {results_dir}")
        return
    
    print(f"📁 Scanning results directory: {results_dir}")
    
    # Process each result file
    total_vcs_added = 0
    total_vcs_skipped = 0
    files_processed = 0
    
    for filename in sorted(os.listdir(results_dir)):
        if not filename.endswith('.json'):
            continue
            
        # Only process completed files (skip in_progress)
        if 'completed' not in filename:
            print(f"⏩ Skipping non-completed file: {filename}")
            continue
            
        print(f"\n📄 Processing: {filename}")
        
        # Extract page number
        page_number = extract_page_number_from_filename(filename)
        if page_number is None:
            print(f"⚠️  Could not extract page number from: {filename}")
            continue
            
        print(f"   📍 Page number: {page_number}")
        
        # Load file
        file_path = os.path.join(results_dir, filename)
        results_data = load_result_file(file_path)
        if results_data is None:
            continue
            
        # Extract VC data
        vcs = extract_vc_data_from_results(results_data, page_number, filename)
        print(f"   🔍 Found {len(vcs)} VCs in file")
        
        # Add each VC to cache
        file_added = 0
        file_skipped = 0
        
        for vc in vcs:
            slug = vc['slug']
            
            # Check if already in cache
            if cache_manager.get_vc_status(slug) is not None:
                print(f"     ⏩ Already in cache: {slug}")
                file_skipped += 1
                continue
                
            # Add to cache
            success = cache_manager.add_vc(
                slug=slug,
                name=vc['name'],
                url=vc['url'],
                first_seen_page=vc['page_number']
            )
            
            if success:
                # Mark as completed with scraped timestamp
                cache_manager.mark_vc_completed(slug)
                
                # Update last_scraped if we have the timestamp
                if vc['scraped_at']:
                    cache_manager.cache_data[slug]['last_scraped'] = vc['scraped_at']
                    cache_manager.cache_data[slug]['last_updated'] = vc['scraped_at']
                    cache_manager._save_cache()
                
                print(f"     ✅ Added: {slug} ({vc['name'][:30]}...)")
                file_added += 1
            else:
                print(f"     ❌ Failed to add: {slug}")
                file_skipped += 1
        
        total_vcs_added += file_added
        total_vcs_skipped += file_skipped
        files_processed += 1
        
        print(f"   📊 File summary: {file_added} added, {file_skipped} skipped")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 CACHE POPULATION COMPLETE")
    print("=" * 60)
    print(f"📁 Files processed: {files_processed}")
    print(f"✅ VCs added to cache: {total_vcs_added}")
    print(f"⏩ VCs skipped (already in cache): {total_vcs_skipped}")
    
    # Show final cache stats
    final_stats = cache_manager.get_cache_stats()
    print(f"\n📊 Final cache statistics:")
    cache_manager.print_cache_stats()
    
    print(f"\n💾 Cache file location: {cache_manager.cache_file_path}")
    print("✅ Cache population completed successfully!")


if __name__ == "__main__":
    populate_cache_from_results()