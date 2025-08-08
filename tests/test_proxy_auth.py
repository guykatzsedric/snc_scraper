#!/usr/bin/env python3
"""
Test script for BrightData proxy authentication
Tests proxy connection before integrating into main scraper
"""

import json
import os
import tempfile
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def load_proxy_config(customer_id="ohad-hollander-915907185"):
    """Load proxy configuration from credentials.json for specific customer"""
    try:
        # Look for credentials.json in the chief_os directory
        credentials_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "credentials.json")
        credentials_path = os.path.abspath(credentials_path)
        
        print(f"🔍 Looking for credentials at: {credentials_path}")
        print(f"👤 Customer ID: {customer_id}")
        
        if not os.path.exists(credentials_path):
            print("❌ credentials.json not found")
            return None
            
        with open(credentials_path, 'r') as f:
            config = json.load(f)
            
        # Get customer config
        customer_config = config.get(customer_id)
        if not customer_config:
            print(f"❌ Customer '{customer_id}' not found in credentials.json")
            print(f"Available customers: {list(config.keys())}")
            return None
            
        # Get proxy config for this customer
        proxy_config = customer_config.get('proxy_config')
        if not proxy_config:
            print(f"❌ proxy_config not found for customer '{customer_id}'")
            return None
            
        print("✅ Proxy config loaded successfully")
        print(f"   🌐 Endpoint: {proxy_config['endpoint']}:{proxy_config['port']}")
        print(f"   🌍 Country: {proxy_config['country']}")
        print(f"   🎯 Session: {proxy_config['session']}")
        return proxy_config
        
    except Exception as e:
        print(f"❌ Error loading proxy config: {e}")
        return None

def create_proxy_auth_extension(username, password):
    """Create temporary Chrome extension for proxy authentication"""
    try:
        # Create temporary directory for extension
        extension_dir = tempfile.mkdtemp()
        
        # Create manifest.json
        manifest = {
            "manifest_version": 2,
            "name": "Proxy Auth",
            "version": "1.0",
            "permissions": ["webRequest", "webRequestBlocking", "<all_urls>"],
            "background": {"scripts": ["background.js"]}
        }
        
        manifest_path = os.path.join(extension_dir, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # Create background.js with better error handling
        background_js = f"""
chrome.webRequest.onAuthRequired.addListener(
  function(details) {{
    console.log('Proxy auth requested for:', details.url);
    console.log('Using username:', "{username}");
    return {{
      authCredentials: {{
        username: "{username}",
        password: "{password}"
      }}
    }};
  }},
  {{urls: ["<all_urls>"]}},
  ["blocking"]
);

// Log when extension loads
console.log('Proxy auth extension loaded');
console.log('Username configured:', "{username}");
"""
        
        background_path = os.path.join(extension_dir, "background.js")
        with open(background_path, 'w') as f:
            f.write(background_js)
            
        print(f"✅ Created proxy auth extension at: {extension_dir}")
        return extension_dir
        
    except Exception as e:
        print(f"❌ Error creating extension: {e}")
        return None

def create_test_driver(proxy_config):
    """Create Chrome driver with proxy authentication"""
    try:
        # Build proxy URL components
        endpoint = proxy_config['endpoint']
        port = proxy_config['port']
        username_base = proxy_config['username']
        password = proxy_config['password']
        country = proxy_config.get('country', 'il')
        session = proxy_config.get('session', '123')
        
        # Build full username with country and session
        full_username = f"{username_base}-country-{country}-session-{session}"
        
        print(f"🌐 Proxy endpoint: {endpoint}:{port}")
        print(f"👤 Username: {full_username}")
        print(f"🔒 Password: {'*' * len(password)}")
        
        # Create Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Set proxy server
        proxy_server = f"{endpoint}:{port}"
        chrome_options.add_argument(f"--proxy-server={proxy_server}")
        
        # Create and load proxy auth extension
        extension_dir = create_proxy_auth_extension(full_username, password)
        if extension_dir:
            chrome_options.add_argument(f"--load-extension={extension_dir}")
        else:
            print("❌ Failed to create extension")
            return None
            
        # Create driver
        print("🚀 Starting Chrome with proxy...")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("✅ Chrome driver created successfully")
        return driver, extension_dir
        
    except Exception as e:
        print(f"❌ Error creating driver: {e}")
        return None, None

def test_proxy_connection(driver):
    """Test proxy connection by visiting BrightData's test page"""
    try:
        print("🧪 Testing proxy connection...")
        
        # First, test basic connectivity
        print("🔗 Testing basic connectivity...")
        driver.get("https://httpbin.org/ip")
        time.sleep(5)
        
        basic_response = driver.page_source
        print("📄 Basic IP test response:")
        print(basic_response[:300] + "..." if len(basic_response) > 300 else basic_response)
        
        # Now test BrightData's geo test page
        test_url = "https://geo.brdtest.com/mygeo.json"
        print(f"🔗 Visiting BrightData test: {test_url}")
        
        driver.get(test_url)
        time.sleep(8)  # Longer wait for proxy
        
        # Get page source (should be JSON with geo info)
        page_source = driver.page_source
        print("📄 BrightData response:")
        print(page_source[:500] + "..." if len(page_source) > 500 else page_source)
        
        # Check current URL for any redirects
        current_url = driver.current_url
        print(f"🔍 Current URL: {current_url}")
        
        # Check if we got valid JSON response
        if "country" in page_source and "ip" in page_source:
            print("✅ Proxy connection successful!")
            return True
        elif "<html>" in page_source and len(page_source) < 100:
            print("❌ Got empty HTML - likely proxy auth failed")
            return False
        else:
            print("❌ Proxy connection failed - unexpected response")
            return False
            
    except Exception as e:
        print(f"❌ Error testing connection: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_extension(extension_dir):
    """Clean up temporary extension directory"""
    try:
        if extension_dir and os.path.exists(extension_dir):
            import shutil
            shutil.rmtree(extension_dir)
            print(f"🗑️ Cleaned up extension: {extension_dir}")
    except Exception as e:
        print(f"⚠️ Error cleaning up extension: {e}")

def main():
    """Main test function"""
    print("🧪 BrightData Proxy Authentication Test")
    print("=" * 50)
    
    # Load proxy config
    proxy_config = load_proxy_config()
    if not proxy_config:
        print("❌ Cannot continue without proxy config")
        return False
    
    driver = None
    extension_dir = None
    
    try:
        # Create driver with proxy
        driver, extension_dir = create_test_driver(proxy_config)
        if not driver:
            print("❌ Failed to create driver")
            return False
        
        # Test connection
        success = test_proxy_connection(driver)
        
        print("\n" + "=" * 50)
        if success:
            print("🎉 PROXY TEST PASSED!")
            print("✅ BrightData proxy authentication working correctly")
            print("💡 Ready to integrate into main scraper")
        else:
            print("❌ PROXY TEST FAILED!")
            print("🔧 Check proxy configuration and credentials")
            
        return success
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
        
    finally:
        # Cleanup
        if driver:
            try:
                driver.quit()
                print("🔒 Browser closed")
            except:
                pass
        cleanup_extension(extension_dir)

if __name__ == "__main__":
    success = main()
    print(f"\n{'🎉 TEST PASSED' if success else '❌ TEST FAILED'}")