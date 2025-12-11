import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import time
import os


class FeatureSpecificationCarexpertSpider(scrapy.Spider):
    name = "feature-specification-carexpert"
    allowed_domains = ["carexpert.com.au"]
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.SpecificationInfoJsonPipeline': 300,
            'sawari-expert.pipelines.SpecificationInfoCsvPipeline': 400,
            'sawari-expert.pipelines.FeatureInfoJsonPipeline': 500,
            'sawari-expert.pipelines.FeatureInfoCsvPipeline': 600,
        },
        'CONCURRENT_REQUESTS': 1,
        'DOWNLOAD_DELAY': 3,
    }

    def __init__(self, start_url=None, *args, **kwargs):
        super(FeatureSpecificationCarexpertSpider, self).__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        else:
            self.start_urls = ["https://www.carexpert.com.au/mg/hs"]

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
            # Extract brand and model from URL
            url_parts = current_url.rstrip('/').split('/')
            if len(url_parts) >= 2:
                brand_name = url_parts[-2].replace('-', ' ').title()
                model_name = url_parts[-1].replace('-', ' ').upper()
            else:
                brand_name = "Unknown"
                model_name = "Unknown"

            self.logger.info(f"Brand: {brand_name}, Model: {model_name}")

            # Wait for page to load completely
            time.sleep(5)
            
            # Save complete HTML for debugging
            self.save_debug_html(driver, model_name)
            
            # Analyze page structure
            self.analyze_page_structure(driver)
            
            # Scroll to load all dynamic content
            self.scroll_page(driver)
            
            # Find all variants
            variants = self.find_variants(driver)
            self.logger.info(f"\nFound {len(variants)} variants to process: {variants}")

            # Process each variant
            for variant_name in variants:
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"Processing variant: {variant_name}")
                self.logger.info(f"{'='*60}")

                # Extract specifications for this variant
                spec_items = self.extract_specifications(driver, model_name, variant_name)
                for item in spec_items:
                    yield item

                # Extract features from specs
                feature_items = self.extract_features(spec_items)
                for item in feature_items:
                    yield item

                self.logger.info(f"Completed {variant_name}: {len(spec_items)} specs, {len(feature_items)} features")

            self.logger.info(f"\nCompleted processing URL {url_index}/{total_urls}")

        except Exception as e:
            self.logger.error(f"[ERROR] Error in main parse: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def save_debug_html(self, driver, model_name):
        """Save complete HTML to debug.html file"""
        try:
            os.makedirs("debug_output", exist_ok=True)
            page_html = driver.page_source
            debug_file = f"debug_output/carexpert_{model_name.replace(' ', '_')}_debug.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(page_html)
            self.logger.info(f"✓ Saved complete HTML to: {debug_file}")
            self.logger.info(f"  HTML size: {len(page_html)} characters")
        except Exception as e:
            self.logger.error(f"Error saving debug HTML: {e}")

    def analyze_page_structure(self, driver):
        """Analyze the page structure to find correct selectors"""
        self.logger.info("\n" + "="*80)
        self.logger.info("ANALYZING PAGE STRUCTURE")
        self.logger.info("="*80)
        
        try:
            # Check for h2 headers
            h2_elements = driver.find_elements(By.TAG_NAME, "h2")
            self.logger.info(f"\nFound {len(h2_elements)} <h2> elements:")
            for i, h2 in enumerate(h2_elements[:10]):
                text = h2.text.strip()
                if text:
                    self.logger.info(f"  H2 #{i+1}: '{text[:80]}'")
            
            # Check for h3 headers
            h3_elements = driver.find_elements(By.TAG_NAME, "h3")
            self.logger.info(f"\nFound {len(h3_elements)} <h3> elements:")
            for i, h3 in enumerate(h3_elements[:20]):
                text = h3.text.strip()
                if text:
                    self.logger.info(f"  H3 #{i+1}: '{text[:80]}'")
            
            # Check for ul/li structures
            ul_elements = driver.find_elements(By.TAG_NAME, "ul")
            total_li = sum(len(ul.find_elements(By.TAG_NAME, "li")) for ul in ul_elements[:10])
            self.logger.info(f"\nFound {len(ul_elements)} <ul> elements with ~{total_li} <li> items")
            
            # Look for variant names in page
            page_html = driver.page_source
            variants_found = []
            for variant in ["Vibe", "Excite", "Essence"]:
                if variant in page_html:
                    variants_found.append(variant)
            self.logger.info(f"\nVariant names found in HTML: {variants_found}")
            
            # Check for spec-related text
            spec_keywords = ["Number Of Speakers", "Connection External", "Audio", "Wheelbase"]
            found_keywords = [kw for kw in spec_keywords if kw in page_html]
            self.logger.info(f"Spec keywords found: {found_keywords[:5]}")
            
            # Look for elements containing "Specs"
            try:
                spec_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Specs')]")
                self.logger.info(f"\nFound {len(spec_elements)} elements containing 'Specs'")
                for i, elem in enumerate(spec_elements[:5]):
                    self.logger.info(f"  Specs #{i+1}: tag={elem.tag_name}, text='{elem.text[:60]}'")
            except Exception as e:
                self.logger.debug(f"Error finding specs elements: {e}")
            
            self.logger.info("="*80 + "\n")
            
        except Exception as e:
            self.logger.error(f"Error analyzing page: {e}")

    def scroll_page(self, driver):
        """Scroll page to load all dynamic content"""
        self.logger.info("Scrolling to load all content...")
        try:
            # Scroll down in steps
            for i in range(10):
                driver.execute_script(f"window.scrollTo(0, {i * 1000});")
                time.sleep(0.5)
            
            # Scroll to bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            self.logger.info("✓ Scrolling complete")
        except Exception as e:
            self.logger.error(f"Error scrolling page: {e}")

    def find_variants(self, driver):
        """Find all variant names on the page"""
        variants = []
        variant_names = ["Vibe", "Excite", "Essence"]
        
        try:
            # Method 1: Look for h3 elements with variant names
            self.logger.info("Searching for variants...")
            for variant in variant_names:
                try:
                    elems = driver.find_elements(By.XPATH, f"//h3[contains(text(), '{variant}')]")
                    if elems and variant not in variants:
                        variants.append(variant)
                        self.logger.info(f"  ✓ Found variant: {variant} (via h3)")
                except:
                    pass
            
            # Method 2: Look for any element with variant text
            if not variants:
                for variant in variant_names:
                    try:
                        elems = driver.find_elements(By.XPATH, f"//*[text()='{variant}']")
                        if elems and variant not in variants:
                            variants.append(variant)
                            self.logger.info(f"  ✓ Found variant: {variant} (via text match)")
                    except:
                        pass
            
            # Method 3: Check in page source
            if not variants:
                page_text = driver.page_source
                for variant in variant_names:
                    if variant in page_text and variant not in variants:
                        variants.append(variant)
                        self.logger.info(f"  ✓ Found variant: {variant} (in page source)")
            
            # Default to all variants if none found
            if not variants:
                self.logger.warning("No variants detected, using all known variants")
                variants = variant_names
                
        except Exception as e:
            self.logger.error(f"Error finding variants: {e}")
            variants = variant_names
        
        return variants

    def extract_specifications(self, driver, model_name, variant_name):
        """Extract specifications for a specific variant"""
        all_specs = []
        
        try:
            # Try to find and scroll to variant section
            try:
                variant_elem = driver.find_element(By.XPATH, f"//*[contains(text(), '{variant_name}')]")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", variant_elem)
                time.sleep(2)
                self.logger.info(f"✓ Scrolled to {variant_name} section")
            except:
                self.logger.warning(f"Could not find {variant_name} section")
            
            # Click expand button if present
            try:
                expand_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Expand') or contains(text(), 'expand')]")
                for btn in expand_btns:
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        time.sleep(1)
                        self.logger.info("✓ Clicked expand button")
                    except:
                        pass
            except:
                pass
            
            # Try multiple XPath patterns to find spec items
            spec_lists = []
            xpath_patterns = [
                f"//h3[contains(text(), '{variant_name}')]/following-sibling::ul[1]//li",
                f"//h3[contains(text(), '{variant_name}')]/following-sibling::*//li",
                f"//*[contains(text(), '{variant_name}')]/following-sibling::ul//li",
                "//h2[contains(text(), 'Specs')]/following-sibling::*//ul//li",
                "//ul/li[contains(text(), ':')]",
            ]
            
            for idx, xpath in enumerate(xpath_patterns):
                try:
                    items = driver.find_elements(By.XPATH, xpath)
                    if items and len(items) > 5:
                        spec_lists = items
                        self.logger.info(f"✓ Found {len(items)} specs using pattern #{idx+1}")
                        break
                except:
                    pass
            
            if not spec_lists:
                self.logger.warning(f"No specs found for {variant_name}")
                return all_specs
            
            # Parse spec items
            current_category = "General"
            
            for item in spec_lists:
                try:
                    text = item.text.strip()
                    if not text:
                        continue
                    
                    # Check if it's a category header (bold/strong text without colon)
                    try:
                        strong = item.find_element(By.XPATH, ".//strong | .//b")
                        if strong and strong.text.strip() == text and ':' not in text:
                            current_category = text
                            continue
                    except:
                        pass
                    
                    # Check if this is a multi-line grouped item (contains newlines)
                    if '\n' in text:
                        # Parse each line within this grouped item
                        lines = text.split('\n')
                        first_line = lines[0].strip()
                        
                        # Check if first line is a category name (no colon)
                        if ':' not in first_line and len(lines) > 1:
                            # First line is subcategory, rest are specs
                            sub_category = first_line
                            for line in lines[1:]:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                # Parse this line as "Name: Value"
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    spec_name = re.sub(r'^[-•\s]+', '', parts[0].strip())
                                    spec_value = re.sub(r'^[-•\s]+', '', parts[1].strip())
                                    
                                    if spec_name and spec_value:
                                        all_specs.append({
                                            "modelName": model_name,
                                            "makeYear": 2025,
                                            "variantName": variant_name,
                                            "specificationCategoryName": sub_category,
                                            "specificationName": spec_name,
                                            "specificationValue": spec_value,
                                        })
                                else:
                                    # Line without colon - treat as feature (value = Yes)
                                    spec_name = re.sub(r'^[-•\s]+', '', line)
                                    if spec_name and len(spec_name) < 150:
                                        all_specs.append({
                                            "modelName": model_name,
                                            "makeYear": 2025,
                                            "variantName": variant_name,
                                            "specificationCategoryName": sub_category,
                                            "specificationName": spec_name,
                                            "specificationValue": "Yes",
                                        })
                        else:
                            # All lines are specs with Name: Value format
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                
                                if ':' in line:
                                    parts = line.split(':', 1)
                                    spec_name = re.sub(r'^[-•\s]+', '', parts[0].strip())
                                    spec_value = re.sub(r'^[-•\s]+', '', parts[1].strip())
                                    
                                    if spec_name and spec_value:
                                        all_specs.append({
                                            "modelName": model_name,
                                            "makeYear": 2025,
                                            "variantName": variant_name,
                                            "specificationCategoryName": current_category,
                                            "specificationName": spec_name,
                                            "specificationValue": spec_value,
                                        })
                    else:
                        # Single line item
                        if ':' in text:
                            # Parse as "Name: Value"
                            parts = text.split(':', 1)
                            spec_name = re.sub(r'^[-•\s]+', '', parts[0].strip())
                            spec_value = re.sub(r'^[-•\s]+', '', parts[1].strip())
                            
                            if spec_name and spec_value:
                                all_specs.append({
                                    "modelName": model_name,
                                    "makeYear": 2025,
                                    "variantName": variant_name,
                                    "specificationCategoryName": current_category,
                                    "specificationName": spec_name,
                                    "specificationValue": spec_value,
                                })
                        else:
                            # No colon - treat as feature (value = Yes)
                            spec_name = re.sub(r'^[-•\s]+', '', text)
                            if spec_name and len(spec_name) < 150:
                                all_specs.append({
                                    "modelName": model_name,
                                    "makeYear": 2025,
                                    "variantName": variant_name,
                                    "specificationCategoryName": current_category,
                                    "specificationName": spec_name,
                                    "specificationValue": "Yes",
                                })
                            
                except Exception as e:
                    continue
            
            self.logger.info(f"Total specs extracted for {variant_name}: {len(all_specs)}")
            
        except Exception as e:
            self.logger.error(f"Error extracting specs: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
        
        return all_specs

    def extract_features(self, spec_items):
        """Convert specs to features where applicable"""
        all_features = []
        
        feature_categories = [
            "Audio", "Convenience", "Safety", "Entertainment",
            "Comfort", "Technology", "Interior trim", "Visibility",
            "Lights", "Instrumentation"
        ]
        
        try:
            for spec in spec_items:
                category = spec.get("specificationCategoryName", "")
                
                # Check if this spec belongs to a feature category
                if any(feat_cat.lower() in category.lower() for feat_cat in feature_categories):
                    all_features.append({
                        "modelName": spec["modelName"],
                        "makeYear": spec["makeYear"],
                        "variantName": spec["variantName"],
                        "featureCategoryName": category,
                        "featureName": spec["specificationName"],
                        "featureValue": spec["specificationValue"],
                        "featureIsHighlighted": "",
                    })
            
            self.logger.info(f"Converted {len(all_features)} specs to features")
            
        except Exception as e:
            self.logger.error(f"Error extracting features: {e}")
        
        return all_features