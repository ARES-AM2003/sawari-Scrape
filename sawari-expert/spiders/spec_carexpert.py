import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
import os


class SpecCarexpertSpider(scrapy.Spider):
    name = "spec-carexpert"
    allowed_domains = ["carexpert.com.au"]
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.SpecificationInfoCsvPipeline': 400,
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super(SpecCarexpertSpider, self).__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        else:
            self.start_urls = ["https://www.carexpert.com.au/mg/hs/2025-vibe-jsawk8g520250601"]
        
        # Parse URL to set brand and model for pipeline
        url = self.start_urls[0] if self.start_urls else ""
        url_parts = url.rstrip('/').split('/')
        
        if len(url_parts) >= 5:
            self.brand_name = url_parts[-3].replace('-', ' ').title()
            self.model_name = url_parts[-2].replace('-', ' ').upper()
        elif len(url_parts) >= 4:
            self.brand_name = url_parts[-2].replace('-', ' ').title()
            self.model_name = url_parts[-1].replace('-', ' ').upper()
        else:
            self.brand_name = "Unknown"
            self.model_name = "Unknown"

    def start_requests(self):
        for index, url in enumerate(self.start_urls, 1):
            self.logger.info(f"Processing URL {index}/{len(self.start_urls)}: {url}")
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                wait_time=20,
                screenshot=True,
                dont_filter=True,
                meta={
                    'dont_cache': True,
                    'url_index': index,
                    'total_urls': len(self.start_urls)
                }
            )

    def parse(self, response):
        url_index = response.meta.get('url_index', 0)
        total_urls = response.meta.get('total_urls', 0)
        current_url = response.url

        self.logger.info(f"=" * 80)
        self.logger.info(f"PARSING URL {url_index}/{total_urls}: {current_url}")
        self.logger.info(f"=" * 80)

        driver = response.meta.get("driver")
        if not driver:
            self.logger.error(f"WebDriver not found in response for URL: {current_url}")
            return

        try:
            # Parse URL to extract brand, model, year, and variant
            # Format: /brand/model/year-variant-variantcode
            url_parts = current_url.rstrip('/').split('/')
            
            # Check if this is a variant-specific URL
            if len(url_parts) >= 5 and '-' in url_parts[-1]:
                # Variant-specific URL
                brand_name = url_parts[-3].replace('-', ' ').title()
                model_name = url_parts[-2].replace('-', ' ').upper()
                
                # Parse the variant part: year-variant-code
                variant_part = url_parts[-1]
                variant_parts = variant_part.split('-')
                
                if len(variant_parts) >= 2:
                    make_year = variant_parts[0]
                    variant_name = variant_parts[1].replace('-', ' ').title()
                else:
                    make_year = "2025"
                    variant_name = variant_part.split('-')[0].title() if '-' in variant_part else "Unknown"
                    
            elif len(url_parts) >= 4:
                # General model URL
                brand_name = url_parts[-2].replace('-', ' ').title()
                model_name = url_parts[-1].replace('-', ' ').upper()
                make_year = "2025"
                variant_name = "Unknown"
            else:
                brand_name = "Unknown"
                model_name = "Unknown"
                make_year = "2025"
                variant_name = "Unknown"

            self.logger.info(f"Brand: {brand_name}, Model: {model_name}, Year: {make_year}, Variant: {variant_name}")

            # Set spider attributes for pipeline
            self.brand_name = brand_name
            self.model_name = model_name

            # Wait for page to load completely
            time.sleep(5)
            
            # Save complete HTML for debugging
            self.save_debug_html(driver, model_name, variant_name)
            
            # Scroll to load all dynamic content
            self.scroll_page(driver)
            
            # Extract specifications
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Extracting specifications for {variant_name}")
            self.logger.info(f"{'='*60}")

            spec_items = self.extract_specifications(driver, model_name, variant_name, make_year)
            
            for item in spec_items:
                yield item

            self.logger.info(f"Completed {variant_name}: {len(spec_items)} specifications extracted")
            self.logger.info(f"\nCompleted processing URL {url_index}/{total_urls}")

        except Exception as e:
            self.logger.error(f"[ERROR] Error in main parse: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def save_debug_html(self, driver, model_name, variant_name):
        """Save complete HTML to debug.html file"""
        try:
            os.makedirs("debug_output", exist_ok=True)
            page_html = driver.page_source
            
            if variant_name and variant_name != "Unknown":
                debug_file = f"debug_output/carexpert_{model_name.replace(' ', '_')}_{variant_name.replace(' ', '_')}_debug.html"
            else:
                debug_file = f"debug_output/carexpert_{model_name.replace(' ', '_')}_debug.html"
            
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(page_html)
            self.logger.info(f"✓ Saved complete HTML to: {debug_file}")
            self.logger.info(f"  HTML size: {len(page_html)} characters")
        except Exception as e:
            self.logger.error(f"Error saving debug HTML: {e}")

    def scroll_page(self, driver):
        """Scroll page progressively to load dynamic content"""
        try:
            self.logger.info("\nScrolling page to load dynamic content...")
            
            # Get initial height
            last_height = driver.execute_script("return document.body.scrollHeight")
            
            scroll_pause = 2
            max_scrolls = 10
            scrolls = 0
            
            while scrolls < max_scrolls:
                # Scroll down
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                
                # Calculate new height
                new_height = driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    break
                    
                last_height = new_height
                scrolls += 1
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            self.logger.info(f"✓ Completed scrolling ({scrolls} scrolls)")
            
        except Exception as e:
            self.logger.error(f"Error scrolling page: {e}")

    def extract_specifications(self, driver, model_name, variant_name, make_year):
        """Extract specifications for the variant"""
        all_specs = []
        
        # Category mapping
        category_mapping = {
            'Engine': 'Engine & Transmission',
            'Transmission & Drivetrain': 'Engine & Transmission',
            'Fuel': 'Capacity',
            'Wheels & Tyres': 'Suspensions, Brakes, Steering & Tyres',
            'Dimensions & Weights': 'Dimensions & Weight',
            'Other': 'Capacity',
            'Safety': 'Suspensions, Brakes, Steering & Tyres'
        }
        
        try:
            # Try to find and scroll to specs section
            try:
                specs_headers = driver.find_elements(By.XPATH, "//h2[contains(text(), 'Specs') or contains(text(), 'Specifications')]")
                if specs_headers:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", specs_headers[0])
                    time.sleep(2)
                    self.logger.info("✓ Scrolled to Specifications section")
            except:
                pass
            
            # Click expand buttons if present
            try:
                expand_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Show') or contains(text(), 'Expand') or contains(text(), 'expand')]")
                for btn in expand_btns:
                    try:
                        if btn.is_displayed():
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(1)
                            self.logger.info("✓ Clicked expand button")
                    except:
                        pass
            except:
                pass
            
            # Find all accordion sections with tables
            try:
                # Look for accordion sections containing tables
                accordion_sections = driver.find_elements(By.XPATH, "//div[@data-testid='accordion']")
                self.logger.info(f"✓ Found {len(accordion_sections)} accordion sections")
                
                if not accordion_sections:
                    self.logger.warning(f"No accordion sections found for {variant_name}")
                    return all_specs
                    
            except Exception as e:
                self.logger.error(f"Error finding accordion sections: {e}")
                return all_specs
            
            # Parse each accordion section
            for section in accordion_sections:
                try:
                    # Get category name from accordion header
                    try:
                        category_header = section.find_element(By.XPATH, ".//span[@data-testid='accordion-header-title-text']")
                        original_category_name = category_header.text.strip()
                        # Map to desired category name
                        category_name = category_mapping.get(original_category_name, 'Capacity')
                    except:
                        category_name = "Capacity"
                    
                    self.logger.debug(f"Processing category: {original_category_name} -> {category_name}")
                    
                    # Find all table rows in this section
                    try:
                        rows = section.find_elements(By.XPATH, ".//table//tr")
                        
                        for row in rows:
                            try:
                                # Get th (spec name) and td (spec value)
                                th = row.find_element(By.XPATH, ".//th")
                                td = row.find_element(By.XPATH, ".//td")
                                
                                spec_name = th.text.strip()
                                spec_value = td.text.strip()
                                
                                # Skip only if spec name is empty
                                if not spec_name:
                                    continue
                                
                                # Keep all values including "-" and empty ones
                                all_specs.append({
                                    "modelName": model_name,
                                    "makeYear": int(make_year) if make_year.isdigit() else 2025,
                                    "variantName": variant_name,
                                    "specificationCategoryName": category_name,
                                    "specificationName": spec_name,
                                    "specificationValue": spec_value,
                                })
                                
                            except Exception as e:
                                self.logger.debug(f"Error parsing row: {e}")
                                continue
                                
                    except Exception as e:
                        self.logger.debug(f"No table found in section {category_name}: {e}")
                        continue
                        
                except Exception as e:
                    self.logger.debug(f"Error parsing section: {e}")
                    continue
            
            self.logger.info(f"Total specifications extracted for {variant_name}: {len(all_specs)}")
            
        except Exception as e:
            self.logger.error(f"Error extracting specifications: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return all_specs