# Scrapy settings for sawariexpert project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "sawari-expert"

SPIDER_MODULES = ["sawari-expert.spiders"]
NEWSPIDER_MODULE = "sawari-expert.spiders"

ADDONS = {}

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:114.0) Gecko/20100101 Firefox/114.0"  # Example Firefox User-Agent
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False  # Set to False to allow scraping if the website blocks by robots.txt

# Concurrency and throttling settings
CONCURRENT_REQUESTS = 16  # Default is 16 requests, feel free to adjust as per the server load
CONCURRENT_REQUESTS_PER_DOMAIN = 4  # Now safe with multiple tabs! 4 parallel requests per domain
DOWNLOAD_DELAY = 0.5  # Reduced delay since we're using tabs efficiently

# Disabling cookies by default for cleaner scraping, unless the website needs cookies.
COOKIES_ENABLED = False  # Set to True if the website requires cookies for functionality

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False  # Disable Telnet console to avoid unnecessary overhead

# Enable or disable spider middlewares
# SPIDER_MIDDLEWARES = {
#     "sawariexpert.middlewares.SawariexpertSpiderMiddleware": 543,
# }
# Middleware is helpful if you need custom logic for item processing during crawling.

# Enable or disable downloader middlewares
# DOWNLOADER_MIDDLEWARES = {
#     'sawariexpert.middlewares.SeleniumMiddleware': 800,
# }

# ✅ Selenium Multi-Tab Settings (Each Browser Instance Uses Multiple Tabs)
SELENIUM_MAX_TABS = 4  # Number of tabs per browser instance
SELENIUM_BROWSER = 'firefox'  # 'firefox' or 'chrome'

# Configure item pipelines
# ITEM_PIPELINES = {
#     "sawari-expert.pipelines.ModelInfoJsonPipeline": 300,
#     "sawari-expert.pipelines.ModelInfoCsvPipeline": 400,
#     "sawari-expert.pipelines.ColourOptionsInfoJsonPipeline": 500,
#     "sawari-expert.pipelines.ColourOptionsInfoCsvPipeline": 600,
#     "sawari-expert.pipelines.VariantInfoJsonPipeline": 700,
#     "sawari-expert.pipelines.VariantInfoCsvPipeline": 800,
#     "sawari-expert.pipelines.SpecificationInfoJsonPipeline": 900,
#     "sawari-expert.pipelines.SpecificationInfoCsvPipeline": 1000,
#     "sawari-expert.pipelines.FeatureInfoJsonPipeline": 1100,
#     "sawari-expert.pipelines.FeatureInfoCsvPipeline": 1200
# }
# Pipeline settings can be customized based on the data processing needs.

# Enable and configure the AutoThrottle extension (disabled by default)
AUTOTHROTTLE_ENABLED = True  # AutoThrottle is useful to avoid hammering the server
AUTOTHROTTLE_START_DELAY = 5  # Initial delay when starting requests
AUTOTHROTTLE_MAX_DELAY = 60  # Maximum delay in case of high latencies
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0  # Adjust requests based on the server response time
AUTOTHROTTLE_DEBUG = False  # Disable debug output for performance

# Enable and configure HTTP caching (disabled by default)
HTTPCACHE_ENABLED = True  # HTTP Cache saves the responses to avoid re-scraping during development
HTTPCACHE_EXPIRATION_SECS = 86400  # Cache expires in 24 hours
HTTPCACHE_DIR = "httpcache"  # Directory to store cache
HTTPCACHE_IGNORE_HTTP_CODES = []  # Define which HTTP codes to cache (useful for specific status codes)
HTTPCACHE_STORAGE = "scrapy.extensions.httpcache.FilesystemCacheStorage"  # Use filesystem cache storage

# Set settings whose default value is deprecated to a future-proof value
FEED_EXPORT_ENCODING = "utf-8"  # Ensure the output file is saved in UTF-8 encoding (for international characters)

# **Selenium Settings:**
DOWNLOADER_MIDDLEWARES = {
    'sawari-expert.middlewares.SeleniumMiddleware': 543,  # Single browser with multiple tabs
    # Other middlewares can be added here
}

# 💡 Performance Notes with Multi-Tab Setup:
# - SELENIUM_MAX_TABS=4: Each browser has 4 tabs (~550MB per browser)
# - CONCURRENT_REQUESTS_PER_DOMAIN=4: Matches tab count for optimal performance
# - Single browser with 4 tabs: ~550MB (vs 1800MB for 4 separate browsers)
# - 3 browsers × 4 tabs each = 12 concurrent requests (~1.65GB total)
# - Your 8GB RAM can comfortably handle 3-4 browsers with 4 tabs each
# - Adjust run_variants_parallel.py to set NUM_BROWSERS and TABS_PER_BROWSER


# Selenium settings for Firefox

# Selenium settings for Firefox
# from webdriver_manager.firefox import GeckoDriverManager

# SELENIUM_DRIVER_NAME = 'firefox'
# SELENIUM_DRIVER_EXECUTABLE_PATH = GeckoDriverManager().install()  # ✅ Verified
# SELENIUM_DRIVER_ARGUMENTS = ['-headless']


# Updated selenium driver initialization
# SELENIUM_DRIVER_SERVICE = Service(executable_path=SELENIUM_DRIVER_EXECUTABLE_PATH)

# Other best practices you can add based on your needs:
# Retry Mechanism: To handle network failures or timeouts
RETRY_TIMES = 3  # Retry 3 times on failure
DOWNLOAD_TIMEOUT = 30  # Timeout in 30 seconds for each download attempt
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408]  # Retry on specific HTTP errors

# **Data Export Options (optional):**
FEEDS = {
    # 'output/cars.json': {'format': 'json'},  # Export data as JSON
    # 'output/cars.csv': {'format': 'csv'},  # Export data as CSV
}

# Alternative User-Agent string (use if you need to rotate UA for bypassing bot checks):
# USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
# This can be randomly rotated using additional middleware like scrapy-fake-useragent or proxy services.

# **Other Notes:**
# 1. **Concurrency/Download Delay:** Lowering `CONCURRENT_REQUESTS_PER_DOMAIN` helps to avoid overwhelming the website.
# 2. **AutoThrottle:** Ideal for controlling request rates dynamically based on website load.
# 3. **Caching:** Enables caching to avoid redundant requests during development.
# 4. **Cookies:** If the website uses cookies for session tracking, consider enabling cookies.


