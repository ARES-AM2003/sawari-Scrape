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


# ✅ Custom Selenium Middleware
class SeleniumMiddleware:

    def __init__(self, browser="firefox"):
        if browser == "chrome":
            options = ChromeOptions()
            # options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")

            # Try system driver first, then download if needed
            driver_path = self._get_driver_path("chrome")
            service = ChromeService(driver_path)
            self.driver = Chrome(service=service, options=options)
        else:
            options = FirefoxOptions()
            options.add_argument("--headless")

            # Create profile and add extension
            profile = FirefoxProfile()
            profile.add_extension("/home/ares-am/Projects/BNT/scrapy/utils/uBlock0_1.68.1b0.firefox.xpi")
            
            # Pass profile to options
            options.profile = profile

            # Try system driver first, then download if needed
            driver_path = self._get_driver_path("firefox")
            service = FirefoxService(driver_path)
            self.driver = Firefox(service=service, options=options)

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
        middleware = cls()
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def process_request(self, request, spider):
        spider.logger.info(f"Selenium is processing: {request.url}")
        self.driver.get(request.url)
        body = str.encode(self.driver.page_source)

        response = HtmlResponse(
            self.driver.current_url,
            body=body,
            encoding='utf-8',
            request=request
        )
        response.meta['driver'] = self.driver  # ✅ Inject driver into meta
        return response

    def spider_closed(self):
        self.driver.quit()
# class SeleniumMiddleware:
#     def __init__(self):
#         options = Options()
#         # options.add_argument("--headless")  # Uncomment this to run headless
#         options.add_argument("--disable-gpu")
#         options.add_argument("--no-sandbox")
#         options.add_argument("--disable-dev-shm-usage")
#
#         service = Service(ChromeDriverManager().install())
#         self.driver = Chrome(service=service, options=options)
#
#     @classmethod
#     def from_crawler(cls, crawler):
#         middleware = cls()
#         crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
#         return middleware
#
#     def process_request(self, request, spider):
#         spider.logger.info(f"[Chrome Selenium] Processing URL: {request.url}")
#         self.driver.get(request.url)
#         body = str.encode(self.driver.page_source)
#
#         response = HtmlResponse(
#             url=self.driver.current_url,
#             body=body,
#             encoding='utf-8',
#             request=request
#         )
#         response.meta['driver'] = self.driver  # ✅ Pass driver in response meta
#         return response
#
#     def spider_closed(self):
#         self.driver.quit()
