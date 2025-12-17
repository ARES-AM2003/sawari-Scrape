import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class VariantCarexpertSpider(scrapy.Spider):
    name = "variant-carexpert"
    allowed_domains = ["carexpert.com.au"]
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.VariantInfoJsonPipeline': 300,
            'sawari-expert.pipelines.VariantInfoCsvPipeline': 400,
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super(VariantCarexpertSpider, self).__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        else:
            # Default URL - Ford Ranger XL features and specs page
            self.start_urls = ["https://www.carexpert.com.au/ford/ranger/xl/features-and-specs"]

    def start_requests(self):
        for url in self.start_urls:
            self.logger.info(f"Starting with URL: {url}")
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                wait_time=20,
                screenshot=True,
                dont_filter=True,
                meta={'dont_cache': True}
            )

    def parse(self, response):
        """Parse the model page and extract all variant configurations"""
        driver = response.meta['driver']
        
        try:
            # Wait for the configurations section to load
            self.logger.info("Waiting for configurations section...")
            configs_section = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//h5[contains(text(), 'Showing') and contains(text(), 'Configurations')]"))
            )
            self.logger.info("Configurations section found")
            
            # Scroll to configurations
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", configs_section)
            time.sleep(2)
            
            # Find the scrollable container and scroll horizontally to load all variants
            try:
                scrollable_container = driver.find_element(By.XPATH, "//div[@id='scrollable-configuration-sticky-header']")
                self.logger.info("Found scrollable container, scrolling to load all variants...")
                
                # Get the total scrollable width
                scroll_width = driver.execute_script("return arguments[0].scrollWidth;", scrollable_container)
                client_width = driver.execute_script("return arguments[0].clientWidth;", scrollable_container)
                self.logger.info(f"Scrollable width: {scroll_width}, Client width: {client_width}")
                
                # Scroll incrementally to ensure all variants are loaded (lazy loading)
                scroll_position = 0
                scroll_step = client_width // 2  # Scroll half viewport at a time
                
                while scroll_position < scroll_width:
                    driver.execute_script(f"arguments[0].scrollLeft = {scroll_position};", scrollable_container)
                    time.sleep(0.5)  # Give time for lazy loading
                    scroll_position += scroll_step
                
                # Final scroll to the end
                driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth;", scrollable_container)
                time.sleep(1)
                
                # Scroll back to start
                driver.execute_script("arguments[0].scrollLeft = 0;", scrollable_container)
                time.sleep(1)
                
                self.logger.info("Completed scrolling through all variants")
            except Exception as e:
                self.logger.warning(f"Could not scroll container: {e}")
            
            # Find all variant articles within the scrollable container
            try:
                variant_articles = driver.find_elements(By.XPATH, "//div[@id='scrollable-configuration-sticky-header']//article[contains(@class, '_1ivmml53vu')]")
                self.logger.info(f"Found {len(variant_articles)} variant configurations in scrollable container")
            except Exception as e:
                self.logger.warning(f"Could not find variants in scrollable container, trying global search: {e}")
                variant_articles = driver.find_elements(By.XPATH, "//article[contains(@class, '_1ivmml53vu')]")
                self.logger.info(f"Found {len(variant_articles)} variant configurations globally")
            
            # Extract all variant names first for logging
            variant_names = []
            for article in variant_articles:
                try:
                    config_elem = article.find_element(By.XPATH, ".//p[contains(@class, 'eh3zt05')]")
                    variant_names.append(config_elem.text.strip())
                except:
                    pass
            
            self.logger.info(f"Variant names found: {variant_names}")
            
            for idx, article in enumerate(variant_articles, 1):
                try:
                    variant_data = self.extract_variant_data(article, idx)
                    if variant_data:
                        yield variant_data
                except Exception as e:
                    self.logger.error(f"Error extracting variant {idx}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error parsing page: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def extract_variant_data(self, article, index):
        """Extract variant name from article element"""
        try:
            # Extract variant configuration (p tag with detailed specs)
            variant_name = None
            try:
                config_elem = article.find_element(By.XPATH, ".//p[contains(@class, 'eh3zt05')]")
                variant_name = config_elem.text.strip()
            except Exception as e:
                self.logger.warning(f"Could not extract variant name: {e}")
            
            if not variant_name:
                self.logger.warning(f"Skipping variant {index} - no name found")
                return None
            
            variant_item = {
                        "modelName": "",
                        "makeYear": "",
                        "variantName": variant_name,
                        "variantPrice": "",
                        "variantFuelType": "",
                        "variantSeatingCapacity": "",
                        "variantType": "",
                        "variantIsPopular": "",
                        "variantMileage": ""
                    }
            
            self.logger.info(f"Extracted variant: {variant_name}")
            return variant_item
            
        except Exception as e:
            self.logger.error(f"Error in extract_variant_data: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None