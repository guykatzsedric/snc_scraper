"""
Driver Factory for SNC Scraper
Creates and configures Selenium WebDriver instances with anti-detection features
Separated from main service to avoid circular imports
"""

import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Phase 4: User Agent Pool for Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

# Phase 4: Screen Resolutions for Variation
SCREEN_RESOLUTIONS = [
    "1920,1080",
    "1366,768", 
    "1440,900",
    "1536,864",
    "1280,720"
]


def create_stealth_driver(proxy=None, user_agent=None, headless=False):
    """Create enhanced stealth driver with anti-detection features"""
    chrome_options = Options()

    # Phase 4: Random user agent if not specified
    if user_agent is None:
        user_agent = random.choice(USER_AGENTS)

    # Phase 4: Random screen resolution
    screen_res = random.choice(SCREEN_RESOLUTIONS)

    # Enhanced stealth mode
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Phase 4: Anti-detection enhancements
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Faster loading
    chrome_options.add_argument("--disable-javascript")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values": {
            "images": 2,  # Block images for speed
            "plugins": 2,
            "popups": 2,
            "geolocation": 2,
            "notifications": 2,
            "media_stream": 2,
        }
    })

    # Headless mode for testing
    if headless:
        chrome_options.add_argument("--headless")

    # Apply user agent and screen resolution
    chrome_options.add_argument(f"--user-agent={user_agent}")
    chrome_options.add_argument(f"--window-size={screen_res}")

    # Phase 4: Proxy support
    if proxy:
        chrome_options.add_argument(f"--proxy-server={proxy}")

    driver = webdriver.Chrome(options=chrome_options)

    # Enhanced stealth scripts
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
    driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")

    return driver