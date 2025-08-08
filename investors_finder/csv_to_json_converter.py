#!/usr/bin/env python3
"""
Simple CSV to JSON Converter for SNC Investor Data
Converts all CSV files in investor_list_csvs/ to unified JSON
"""

import csv
import json
import os
import glob


def clean_excel_format(value):
    """Remove Excel formatting like ="value" and return clean string"""
    if not value:
        return ""
    # Remove Excel quotes and equals formatting
    cleaned = str(value).strip()
    if cleaned.startswith('="') and cleaned.endswith('"'):
        cleaned = cleaned[2:-1]
    return cleaned


def extract_vc_id_from_url(url):
    """Extract VC ID from finder URL"""
    if not url:
        return None
    # Get the last part of URL after final slash
    return url.rstrip('/').split('/')[-1]


def process_csv_file(csv_path):
    """Process single CSV file and return VC data dictionary"""
    vcs = {}
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Clean all values from Excel formatting
                cleaned_row = {key: clean_excel_format(value) for key, value in row.items()}
                
                # Extract VC ID from URL
                finder_url = cleaned_row.get('Finder URL', '')
                vc_id = extract_vc_id_from_url(finder_url)
                
                if vc_id and finder_url:
                    vcs[vc_id] = {
                        'name': cleaned_row.get('Name', ''),
                        'url': finder_url,
                        'type': cleaned_row.get('Type', ''),
                        'investment_stage': cleaned_row.get('Investment Stage', ''),
                        'investments': cleaned_row.get('Investments', ''),
                        'il_investments_2y': cleaned_row.get('IL investments in past 2Y', ''),
                        'managed_assets': cleaned_row.get('Managed Assets', ''),
                        'investment_range': cleaned_row.get('Investment Range', '')
                    }
                    
        print(f"✅ Processed {csv_path}: {len(vcs)} VCs")
        
    except Exception as e:
        print(f"❌ Error processing {csv_path}: {e}")
        
    return vcs


def process_all_csvs():
    """Process all CSV files and create unified JSON"""
    print("🚀 Starting CSV to JSON conversion...")
    
    # Find all CSV files
    csv_pattern = os.path.join("investor_list_csvs", "*.csv")
    csv_files = glob.glob(csv_pattern)
    
    if not csv_files:
        print("❌ No CSV files found in investor_list_csvs/ directory")
        return
        
    print(f"📁 Found {len(csv_files)} CSV files")
    
    # Process all CSV files and merge data
    unified_vcs = {}
    
    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        print(f"📄 Processing: {filename}")
        
        vcs_data = process_csv_file(csv_file)
        
        # Merge into unified dictionary (duplicates will overwrite)
        for vc_id, vc_data in vcs_data.items():
            unified_vcs[vc_id] = vc_data
            
    print(f"\n📊 SUMMARY:")
    print(f"   📁 Processed files: {len(csv_files)}")
    print(f"   🏢 Unique VCs found: {len(unified_vcs)}")
    
    # Save unified JSON
    output_file = "unified_vcs.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_vcs, f, indent=2, ensure_ascii=False)
        
    print(f"💾 Saved unified data: {output_file}")
    print(f"✅ Conversion complete!")
    
    return unified_vcs


def main():
    """Main function"""
    print("=" * 50)
    print("📊 SNC INVESTOR CSV TO JSON CONVERTER")
    print("=" * 50)
    
    # Change to script directory to find CSV files
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Process all CSVs
    unified_data = process_all_csvs()
    
    if unified_data:
        print(f"\n🎉 SUCCESS: {len(unified_data)} unique VCs ready for scraping!")
        print(f"📄 Output file: unified_vcs.json")
    else:
        print("❌ No data processed")


if __name__ == "__main__":
    main()