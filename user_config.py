#!/usr/bin/env python3
"""
Easy User & Proxy Configuration for SNC Scraper

INSTRUCTIONS:
1. Edit the proxy settings below for each user
2. Set the ACTIVE_USER to switch between users
3. No need to restart anything - just edit and run

USER TYPES:
- "rate_limited": Handles ODD pages (1,3,5,7...) ~7 VCs each
- "fresh": Handles EVEN pages (2,4,6,8...) ~50 VCs each
"""

# ===========================================
# EASY CONFIGURATION - EDIT THESE SETTINGS
# ===========================================

# User A Configuration (Rate Limited User)
USER_A = {
    "name": "rate_limited_user",
    "type": "rate_limited",  # Handles odd pages
    "connection_type": "direct",  # Options: "scraperapi", "proxy", "direct"
    "scraperapi_key": "60be60561295191d2578545e419b69b6",  # Your ScraperAPI key (if using scraperapi)
    "scraperapi_country": "IL",  # Country for ScraperAPI IPs
    "proxy": "http://brd-customer-hl_d63ef48d-zone-isp_proxy2-country-il-session-123:ba5p480kss1d@brd.superproxy.io:33335",  # Format: "http://ip:port" or None for no proxy
    "user_agent": None,  # None = auto-rotate from premium pool
    "description": "Rate-limited user handling odd pages (7 VCs each)"
}

# User B Configuration (Fresh User)  
USER_B = {
    "name": "fresh_user", 
    "type": "fresh",  # Handles even pages
    "connection_type": "direct",  # Options: "scraperapi", "proxy", "direct"
    "scraperapi_key": "",  # Your ScraperAPI key (if using scraperapi)
    "scraperapi_country": "CA",  # Different country for User B
    "proxy": None,  # Format: "http://ip:port" or None for no proxy
    "user_agent": None,  # None = auto-rotate from premium pool
    "description": "Fresh user handling even pages (50 VCs each)"
}

# ===========================================
# ACTIVE USER SELECTION - CHANGE THIS TO SWITCH USERS
# ===========================================

# SET ACTIVE USER: "A" or "B"
ACTIVE_USER = "A"  # Change to "B" to use User B

# ===========================================
# EXAMPLE PROXY CONFIGURATIONS (FOR REFERENCE)
# ===========================================

"""
CONNECTION EXAMPLES:

SCRAPERAPI (RECOMMENDED FOR ROTATING IPS):
- connection_type: "scraperapi"
- scraperapi_key: "your_scraperapi_key_here"
- scraperapi_country: "US" (or "CA", "UK", "DE", etc.)

PROXY:
- connection_type: "proxy"
- proxy: "http://proxy.example.com:8080"
- proxy: "socks5://proxy.example.com:1080"
- proxy: "http://username:password@proxy.example.com:8080"

DIRECT CONNECTION:
- connection_type: "direct"
- proxy: None

USER AGENT EXAMPLES:
- Auto (Recommended): None
- Custom: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

QUICK SETUP:
1. Choose connection_type: "scraperapi", "proxy", or "direct"
2. Add your ScraperAPI key or proxy details
3. Set ACTIVE_USER to "A" or "B"
4. Run the scraper
"""

# ===========================================
# EXPERIMENTAL FEATURES (STEP 3) - OPTIONAL
# ===========================================

# EXPERIMENTAL: Enhanced resume detection and progressive processing
# All features disabled by default to ensure zero impact on current workflow
EXPERIMENTAL_CONFIG = {
    "enable_enhanced_resume": False,        # Enhanced resume detection with cache
    "enable_progressive_mode": False,       # Progressive VC processing (future)
    "enable_cache_discovery": False,        # Auto-populate cache from pages
    "enable_cache_filtering": False,        # Use cache for filtering VCs
    "max_vcs_per_run": 50,                 # VC limit for progressive mode
    "experimental_version": "v1"           # Version tracking
}

"""
EXPERIMENTAL FEATURES DOCUMENTATION:

🔬 enable_enhanced_resume: 
   - Uses cache + multi-page verification for smarter resume points
   - Fallback to existing logic if it fails
   - Default: False (uses existing resume logic)

🔬 enable_progressive_mode:
   - Process up to max_vcs_per_run across multiple pages (future feature)
   - Default: False (uses existing single-page mode)

🔬 enable_cache_discovery:
   - Automatically populate cache with VCs discovered on pages
   - Default: False (cache only populated manually)

🔬 enable_cache_filtering:
   - Use cache to filter already-completed VCs
   - Default: False (uses existing file-based filtering)

⚠️  SAFETY: All experimental features default to False
    Existing workflow is preserved and used by default
    To enable: Change flags to True in this config
"""

# ===========================================
# SYSTEM FUNCTIONS - DON'T EDIT BELOW
# ===========================================

def get_active_user_config():
    """Get the configuration for the currently active user"""
    if ACTIVE_USER == "A":
        return USER_A
    elif ACTIVE_USER == "B":
        return USER_B
    else:
        raise ValueError(f"Invalid ACTIVE_USER: {ACTIVE_USER}. Must be 'A' or 'B'")

def get_user_type():
    """Get the type of the active user (rate_limited or fresh)"""
    config = get_active_user_config()
    user_type = config["type"]
    print(f"🔍 DEBUG: Active user: {ACTIVE_USER}, User type: {user_type}")
    return user_type

def get_user_proxy():
    """Get the proxy for the active user"""
    return get_active_user_config()["proxy"]

def get_user_agent():
    """Get the user agent for the active user"""
    return get_active_user_config()["user_agent"]

def get_connection_type():
    """Get the connection type for the active user"""
    return get_active_user_config()["connection_type"]

def get_scraperapi_key():
    """Get the ScraperAPI key for the active user"""
    return get_active_user_config()["scraperapi_key"]

def get_scraperapi_country():
    """Get the ScraperAPI country for the active user"""
    return get_active_user_config()["scraperapi_country"]

def get_user_description():
    """Get a description of the active user"""
    config = get_active_user_config()
    return f"{config['name']}: {config['description']}"

def should_handle_page(page_num):
    """Determine if the active user should handle this page number"""
    user_type = get_user_type()
    
    if user_type == "rate_limited":
        # Handle odd pages (1,3,5,7...)
        return page_num % 2 == 1
    elif user_type == "fresh":
        # Handle even pages (2,4,6,8...)
        return page_num % 2 == 0
    else:
        # Fallback: handle any page
        return True

def get_recommended_pages():
    """Get the recommended page range for the active user"""
    user_type = get_user_type()
    
    if user_type == "rate_limited":
        return "ODD pages (1,3,5,7...) - ~7 VCs each"
    elif user_type == "fresh":
        return "EVEN pages (2,4,6,8...) - ~50 VCs each"
    else:
        return "ANY pages"

def get_experimental_config():
    """Get experimental configuration settings"""
    return EXPERIMENTAL_CONFIG.copy()

def is_experimental_feature_enabled(feature_name):
    """Check if a specific experimental feature is enabled"""
    return EXPERIMENTAL_CONFIG.get(feature_name, False)

def get_max_vcs_per_run():
    """Get the maximum VCs per run for progressive mode"""
    return EXPERIMENTAL_CONFIG.get("max_vcs_per_run", 50)

def print_user_info():
    """Print current user configuration"""
    config = get_active_user_config()
    print("=" * 50)
    print("👤 ACTIVE USER CONFIGURATION")
    print("=" * 50)
    print(f"User: {config['name']}")
    print(f"Type: {config['type']}")
    print(f"Pages: {get_recommended_pages()}")
    print(f"Connection: {config['connection_type']}")
    
    if config['connection_type'] == 'scraperapi':
        api_key = config['scraperapi_key']
        print(f"ScraperAPI Key: {'***' + api_key[-4:] if api_key else 'Not set'}")
        print(f"ScraperAPI Country: {config['scraperapi_country']}")
    elif config['connection_type'] == 'proxy':
        print(f"Proxy: {config['proxy'] or 'Not set'}")
    else:
        print(f"Proxy: None (Direct connection)")
        
    print(f"User Agent: {config['user_agent'] or 'Auto-rotate premium pool'}")
    print(f"Description: {config['description']}")
    print("=" * 50)

def print_experimental_status():
    """Print experimental features status"""
    exp_config = get_experimental_config()
    print("\n🔬 EXPERIMENTAL FEATURES STATUS")
    print("=" * 50)
    
    any_enabled = any(exp_config[key] for key in exp_config if key.startswith('enable_'))
    
    if any_enabled:
        print("⚠️  EXPERIMENTAL MODE: Some features enabled")
        for key, value in exp_config.items():
            if key.startswith('enable_'):
                status = "✅ ENABLED" if value else "❌ Disabled"
                feature_name = key.replace('enable_', '').replace('_', ' ').title()
                print(f"   {feature_name}: {status}")
        print(f"   Max VCs per run: {exp_config['max_vcs_per_run']}")
    else:
        print("✅ STABLE MODE: All experimental features disabled")
        print("   Using existing proven workflow")
        print("   💡 To enable experiments, edit EXPERIMENTAL_CONFIG in user_config.py")
    
    print("=" * 50)

if __name__ == "__main__":
    print_user_info()
    print_experimental_status()
    
    # Test page assignment
    print("\n🧪 PAGE ASSIGNMENT TEST:")
    for page in range(1, 11):
        should_handle = should_handle_page(page)
        marker = "✅" if should_handle else "❌"
        print(f"Page {page}: {marker}")