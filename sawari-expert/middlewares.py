from scrapy import signals
from scrapy.http import HtmlResponse
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver import Firefox, FirefoxProfile
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager
import os
import shutil
import threading
from queue import Queue
import time


# Global singleton - ONE browser per Python process
_GLOBAL_DRIVER = None
_GLOBAL_TAB_POOL = None
_GLOBAL_MAX_TABS = None
_GLOBAL_LOCK = threading.Lock()
_GLOBAL_INSTANCE_LOCK = threading.Lock()


class Project_nameSpiderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        return None

    def process_spider_output(self, response, result, spider):
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class Project_nameDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        return None

    def process_response(self, request, response, spider):
        return response

    def process_exception(self, request, exception, spider):
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


# ✅ Custom Selenium Middleware - GLOBAL SINGLETON (One browser per Python process)
class SeleniumMiddleware:

    def __init__(self, browser="firefox", max_tabs=4):
        """
        Initialize middleware. Uses GLOBAL variables to ensure ONE browser per Python process.
        All middleware instances in the same process share the same browser.

        Args:
            browser: 'firefox' or 'chrome'
            max_tabs: Number of tabs to create for concurrent requests
        """
        global _GLOBAL_DRIVER, _GLOBAL_TAB_POOL, _GLOBAL_MAX_TABS

        import sys

        # Use global lock to ensure only one browser is created per process
        with _GLOBAL_LOCK:
            # Check if browser already exists in this process
            if _GLOBAL_DRIVER is not None:
                print(f"\n{'='*80}", file=sys.stderr)
                print(f"♻️  REUSING GLOBAL BROWSER in PID: {os.getpid()}", file=sys.stderr)
                print(f"   Middleware instance #{id(self)}", file=sys.stderr)
                print(f"   Browser has {_GLOBAL_MAX_TABS} tabs", file=sys.stderr)
                print(f"{'='*80}\n", file=sys.stderr)

                # Use existing global browser
                self.driver = _GLOBAL_DRIVER
                self.tab_pool = _GLOBAL_TAB_POOL
                self.max_tabs = _GLOBAL_MAX_TABS
                self.lock = _GLOBAL_INSTANCE_LOCK
                return

            # First middleware instance in this process - create the browser
            print(f"\n{'='*80}", file=sys.stderr)
            print(f"🚀 CREATING GLOBAL BROWSER - PID: {os.getpid()}", file=sys.stderr)
            print(f"   Middleware instance #{id(self)}", file=sys.stderr)
            print(f"   Browser will have {max_tabs} tabs", file=sys.stderr)
            print(f"{'='*80}\n", file=sys.stderr)

            self.max_tabs = max_tabs
            self.lock = _GLOBAL_INSTANCE_LOCK

            # Create single browser instance
            if browser == "chrome":
                options = ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")

                driver_path = self._get_driver_path("chrome")
                service = ChromeService(driver_path)
                self.driver = Chrome(service=service, options=options)
            else:
                options = FirefoxOptions()
                options.add_argument("--headless")

                # Create profile and add extension
                profile = FirefoxProfile()
                try:
                    profile.add_extension("/home/ares-am/Projects/BNT/scrapy/utils/uBlock0_1.68.1b0.firefox.xpi")
                except:
                    pass  # Extension optional
                
                # Set Firefox to open tabs instead of windows
                profile.set_preference("browser.link.open_newwindow", 3)  # 3 = new tab
                profile.set_preference("browser.link.open_newwindow.restriction", 0)
                profile.set_preference("browser.tabs.loadInBackground", False)
                
                # Pass profile to options
                options.profile = profile

                driver_path = self._get_driver_path("firefox")
                service = FirefoxService(driver_path)
                self.driver = Firefox(service=service, options=options)

            # Create tab pool using Queue (thread-safe)
            self.tab_pool = Queue()

            # Get the initial tab handle
            main_tab = self.driver.current_window_handle
            self.tab_pool.put(main_tab)

            # Open additional tabs (not windows!)
            for i in range(max_tabs - 1):
                # Use JavaScript to open tabs within the same window
                self.driver.execute_script("window.open('', '_blank');")
                time.sleep(0.2)  # Small delay to ensure tab is created

            # Get all tab handles and add to pool
            all_tabs = self.driver.window_handles
            for tab in all_tabs[1:]:  # Skip first tab (already added)
                self.tab_pool.put(tab)

            # Store in GLOBAL variables so ALL instances in this process share this browser
            _GLOBAL_DRIVER = self.driver
            _GLOBAL_TAB_POOL = self.tab_pool
            _GLOBAL_MAX_TABS = self.max_tabs

            print(f"\n{'='*80}", file=sys.stderr)
            print(f"✅ GLOBAL BROWSER CREATED in PID: {os.getpid()}", file=sys.stderr)
            print(f"   • Firefox PID: {self.driver.service.process.pid if hasattr(self.driver.service, 'process') else 'unknown'}", file=sys.stderr)
            print(f"   • Tabs created: {len(all_tabs)}", file=sys.stderr)
            print(f"   • Tab handles: {[t[:8] + '...' for t in all_tabs]}", file=sys.stderr)
            print(f"   • Memory per browser: ~{400 + max_tabs*25}MB", file=sys.stderr)
            print(f"   • Stored in GLOBAL variables (shared by all middleware instances)", file=sys.stderr)
            print(f"{'='*80}\n", file=sys.stderr)

    def _get_driver_path(self, browser):
        """Get driver path - prefer system installed, fallback to cached/download"""
        if browser == "chrome":
            # Check system chromedriver first
            system_driver = shutil.which("chromedriver")
            if system_driver:
                return system_driver

            # Check cache
            cache_dir = os.path.expanduser("~/.wdm_cache")
            cached_path = os.path.join(cache_dir, "chromedriver")
            if os.path.exists(cached_path):
                return cached_path

            # Download and cache
            os.makedirs(cache_dir, exist_ok=True)
            driver_path = ChromeDriverManager().install()
            shutil.copy2(driver_path, cached_path)
            os.chmod(cached_path, 0o755)
            return cached_path
        else:  # firefox
            # Check system geckodriver first
            system_driver = shutil.which("geckodriver")
            if system_driver:
                return system_driver

            # Check cache
            cache_dir = os.path.expanduser("~/.wdm_cache")
            cached_path = os.path.join(cache_dir, "geckodriver")
            if os.path.exists(cached_path):
                return cached_path

            # Download and cache as last resort
            os.makedirs(cache_dir, exist_ok=True)
            driver_path = GeckoDriverManager().install()
            shutil.copy2(driver_path, cached_path)
            os.chmod(cached_path, 0o755)
            return cached_path

    @classmethod
    def from_crawler(cls, crawler):
        """
        Create middleware instance. Will reuse global browser if it exists.
        """
        import sys
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"🔧 from_crawler CALLED in PID: {os.getpid()}", file=sys.stderr)

        # Get settings
        max_tabs = crawler.settings.getint('SELENIUM_MAX_TABS', 4)
        browser = crawler.settings.get('SELENIUM_BROWSER', 'firefox')

        print(f"   • Requested: {browser} with {max_tabs} tabs", file=sys.stderr)
        print(f"   • Global browser exists: {_GLOBAL_DRIVER is not None}", file=sys.stderr)
        print(f"{'='*80}\n", file=sys.stderr)

        # Create middleware instance (will reuse browser via global variables)
        middleware = cls(browser=browser, max_tabs=max_tabs)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        """
        Process request using an available tab from the global pool.
        Thread-safe: blocks if all tabs are busy, waits for one to become available.
        """
        # Get available tab from pool (blocks if all tabs are busy)
        tab_handle = self.tab_pool.get()

        try:
            with self.lock:
                # Switch to this specific tab
                self.driver.switch_to.window(tab_handle)
                spider.logger.info(f"🔄 PID:{os.getpid()} Tab[{tab_handle[:8]}...] processing: {request.url}")

                # Load URL in this tab
                self.driver.get(request.url)

                # Get page source and current URL
                body = str.encode(self.driver.page_source)
                current_url = self.driver.current_url

            # Create response (outside lock to minimize blocking time)
            response = HtmlResponse(
                current_url,
                body=body,
                encoding='utf-8',
                request=request
            )
            response.meta['driver'] = self.driver
            response.meta['tab_handle'] = tab_handle

            return response

        finally:
            # Always return tab to pool for reuse (even if error occurs)
            self.tab_pool.put(tab_handle)

    def spider_closed(self):
        """
        Close the global browser when spider finishes.
        Only the last middleware instance should close it.
        """
        global _GLOBAL_DRIVER, _GLOBAL_TAB_POOL, _GLOBAL_MAX_TABS

        import sys
        print(f"\n{'='*80}", file=sys.stderr)
        print(f"🛑 spider_closed CALLED in PID: {os.getpid()}", file=sys.stderr)
        print(f"   Middleware instance #{id(self)}", file=sys.stderr)

        # Close the global browser if it exists
        with _GLOBAL_LOCK:
            if _GLOBAL_DRIVER is not None:
                try:
                    print(f"   Closing global browser with {_GLOBAL_MAX_TABS} tabs...", file=sys.stderr)
                    _GLOBAL_DRIVER.quit()
                    _GLOBAL_DRIVER = None
                    _GLOBAL_TAB_POOL = None
                    _GLOBAL_MAX_TABS = None
                    print(f"   ✅ Global browser closed successfully", file=sys.stderr)
                except Exception as e:
                    print(f"   ⚠️  Error closing browser: {e}", file=sys.stderr)
            else:
                print(f"   ℹ️  Global browser already closed", file=sys.stderr)

        print(f"{'='*80}\n", file=sys.stderr)
