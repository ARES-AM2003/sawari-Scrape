import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
import re
import time


class FeatureSpecificationFragmentSpider(scrapy.Spider):
    name = "feature-specification-fragment"
    allowed_domains = ["carwale.com"]

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
        super(FeatureSpecificationFragmentSpider, self).__init__(*args, **kwargs)
        if start_url:
            self.start_urls = [start_url]
        else:
            # Default URL - a variant page with radio buttons
            self.start_urls = ["https://www.carwale.com/mahindra-cars/xuv700/ax7-luxury-pack/"]

    def start_requests(self):
        for url in self.start_urls:
            self.logger.info(f"Starting with URL: {url}")
            yield SeleniumRequest(
                url=url,
                callback=self.parse_variant_page,
                wait_time=20,
                screenshot=True,
                dont_filter=True,
                meta={'dont_cache': True}
            )

    def parse_variant_page(self, response):
        """Parse the variant page and extract data for all radio button variants"""
        driver = response.meta.get("driver")
        if not driver:
            self.logger.error("WebDriver not found in response")
            return

        try:
            # Wait for page to load
            self.logger.info("Waiting for page to load...")
            time.sleep(3)

            # Extract base car information (brand and model)
            try:
                car_name_elem = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'o-j6') or contains(@class, 'o-j7') or contains(@class, 'o-j5')]"))
                )
                car_name = car_name_elem.text.strip()
                car_parts = car_name.split()
                brand_name = car_parts[0] if len(car_parts) > 0 else ""
                model_name = car_parts[1] if len(car_parts) > 1 else ""
                self.logger.info(f"Car: {car_name}, Brand: {brand_name}, Model: {model_name}")
            except Exception as e:
                self.logger.error(f"Could not extract car name: {e}")
                brand_name = ""
                model_name = ""

            # Scroll down to find the variants table
            self.logger.info("Looking for variants table...")
            try:
                # Wait for variants table to load
                variants_table = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'o-c')]"))
                )
                self.logger.info("Variants table found")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", variants_table)
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Could not find variants table: {e}")
                return

            # Find all radio buttons in the variants table
            radio_buttons = variants_table.find_elements(By.XPATH, ".//input[@type='radio']")
            self.logger.info(f"Found {len(radio_buttons)} radio button variants")

            if len(radio_buttons) == 0:
                self.logger.warning("No radio buttons found. Extracting current page data only.")
                # Extract data for the current variant
                variant_name = self.get_current_variant_name(driver)
                self.logger.info(f"Current variant: {variant_name}")

                # Extract specs and features for current variant
                spec_items = self.extract_specifications(driver, model_name, variant_name)
                for item in spec_items:
                    yield item

                feature_items = self.extract_features(driver, model_name, variant_name)
                for item in feature_items:
                    yield item

                return

            # Process each radio button variant
            for radio_idx in range(len(radio_buttons)):
                try:
                    self.logger.info(f"\n{'='*80}")
                    self.logger.info(f"Processing radio button {radio_idx + 1}/{len(radio_buttons)}")
                    self.logger.info(f"{'='*80}")

                    # Re-find the variants table and radio buttons (to avoid stale element)
                    variants_table = driver.find_element(By.XPATH, "//table[contains(@class, 'o-c')]")
                    radio_buttons_refreshed = variants_table.find_elements(By.XPATH, ".//input[@type='radio']")

                    if radio_idx >= len(radio_buttons_refreshed):
                        self.logger.warning(f"Radio button {radio_idx} no longer exists, skipping")
                        continue

                    current_radio = radio_buttons_refreshed[radio_idx]

                    # Scroll to radio button
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_radio)
                    time.sleep(1)

                    # Click the radio button
                    try:
                        driver.execute_script("arguments[0].click();", current_radio)
                        self.logger.info(f"Clicked radio button {radio_idx + 1}")
                        time.sleep(3)  # Wait for page to update
                    except Exception as e:
                        self.logger.error(f"Error clicking radio button: {e}")
                        continue

                    # Get the variant name from the page heading (after clicking, DOM updates)
                    variant_name = self.get_current_variant_name(driver)
                    self.logger.info(f"Variant name: {variant_name}")

                    # Check if URL has fragment
                    current_url = driver.current_url
                    if '#vid=' in current_url:
                        vid = current_url.split('#vid=')[1].split('&')[0]
                        self.logger.info(f"VID: {vid}")

                    # Scroll to top to access tabs
                    driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(2)

                    # Click on Specs & Features tab
                    self.click_specs_features_tab(driver)

                    # Extract specifications
                    self.logger.info(f"Extracting specifications for {variant_name}...")
                    spec_items = self.extract_specifications(driver, model_name, variant_name)
                    self.logger.info(f"Extracted {len(spec_items)} specifications")
                    for item in spec_items:
                        yield item

                    # Extract features
                    self.logger.info(f"Extracting features for {variant_name}...")
                    feature_items = self.extract_features(driver, model_name, variant_name)
                    self.logger.info(f"Extracted {len(feature_items)} features")
                    for item in feature_items:
                        yield item

                    self.logger.info(f"Completed variant {radio_idx + 1}/{len(radio_buttons)}: {variant_name}")

                    # Scroll back to variants table for next iteration
                    variants_table = driver.find_element(By.XPATH, "//table[contains(@class, 'o-c')]")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", variants_table)
                    time.sleep(2)

                except Exception as e:
                    self.logger.error(f"Error processing radio button {radio_idx + 1}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    continue

            self.logger.info(f"\nCompleted all {len(radio_buttons)} variants")

        except Exception as e:
            self.logger.error(f"Error in parse_variant_page: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def get_current_variant_name(self, driver):
        """Get the current variant name from the page heading"""
        try:
            # Wait for the heading to update after clicking radio button
            time.sleep(1)

            # Try h2 with variant info
            variant_heading = driver.find_element(By.XPATH, "//h2[contains(@class, 'o-j7') or contains(@class, 'o-j5') or contains(@class, 'o-j2')]")
            variant_text = variant_heading.text.strip()

            self.logger.info(f"Raw heading text: {variant_text}")

            # Extract variant name (remove "On Road Price" suffix)
            if "On Road Price" in variant_text:
                variant_text = variant_text.split("On Road Price")[0].strip()

            # Remove brand and model from the beginning (e.g., "Kia Carens")
            # Expected format: "Kia Carens Premium (O) 1.5 Petrol 7 STR"
            parts = variant_text.split(maxsplit=2)
            if len(parts) >= 3:
                # Return everything after brand and model
                return parts[2]
            elif len(parts) == 2:
                # Just model and variant
                return parts[1]
            else:
                # Try alternative - look for the variant name in the label of checked radio
                try:
                    checked_radio = driver.find_element(By.XPATH, "//input[@type='radio'][@checked]")
                    label = checked_radio.find_element(By.XPATH, "./ancestor::label")
                    variant_div = label.find_element(By.XPATH, ".//div[contains(@class, 'o-jJ') and contains(@class, 'o-j3')]")
                    variant_from_radio = variant_div.text.strip()
                    if variant_from_radio:
                        return variant_from_radio
                except:
                    pass

                return "Unknown Variant"
        except Exception as e:
            self.logger.error(f"Error getting current variant name: {e}")
            return "Unknown Variant"

    def get_variant_name_from_radio(self, driver, variants_table, radio_idx):
        """Extract variant name from the radio button's label"""
        try:
            # Re-find radio buttons to avoid stale element
            radio_buttons = variants_table.find_elements(By.XPATH, ".//input[@type='radio']")
            if radio_idx >= len(radio_buttons):
                return "Unknown Variant"

            current_radio = radio_buttons[radio_idx]

            # Find the label that contains this radio button
            label = current_radio.find_element(By.XPATH, "./ancestor::label")

            # First try: get from title attribute (most accurate)
            try:
                title_div = label.find_element(By.XPATH, ".//div[@title]")
                variant_name = title_div.get_attribute('title')
                if variant_name:
                    # Extract only the variant part after brand and model
                    # e.g., "Carens Premium (O) 1.5 Petrol 7 STR" -> "Premium (O) 1.5 Petrol 7 STR"
                    parts = variant_name.split(maxsplit=1)
                    if len(parts) > 1:
                        return parts[1]
                    return variant_name
            except:
                pass

            # Second try: get from div text
            try:
                variant_name_div = label.find_element(By.XPATH, ".//div[contains(@class, 'o-jJ') and contains(@class, 'o-j3')]")
                variant_name = variant_name_div.text.strip()
                if variant_name:
                    return variant_name
            except:
                pass

            # Fallback: get from current page heading
            return self.get_current_variant_name(driver)

        except Exception as e:
            self.logger.error(f"Error extracting variant name from radio: {e}")
            return "Unknown Variant"

    def click_specs_features_tab(self, driver):
        """Click on the Specs & Features tab"""
        try:
            # Find and click Specs & Features tab
            specs_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Specs & Features')] | //div[contains(text(), 'Specs & Features')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", specs_tab)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", specs_tab)
            self.logger.info("Clicked Specs & Features tab")
            time.sleep(3)
        except Exception as e:
            self.logger.warning(f"Could not click Specs & Features tab: {e}")
            # May already be on the tab or tab doesn't exist

    def extract_specifications(self, driver, model_name, variant_name):
        """Extract specifications data from the page"""
        all_specs = []

        try:
            # Remove obstructing elements
            try:
                obstructing_elements = [
                    "//button[contains(@class, 'ticker-cta-container-1')]",
                    "//div[contains(@class, 'model-ticker__wrapper')]",
                    "//div[contains(@class, 'ticker')]",
                    "//div[contains(@class, 'popup')]",
                ]
                for xpath in obstructing_elements:
                    try:
                        elements = driver.find_elements(By.XPATH, xpath)
                        for element in elements:
                            driver.execute_script("arguments[0].remove();", element)
                    except:
                        continue
            except:
                pass

            # Find Specifications heading
            specs_heading = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Specifications')] | //h3[text()='Specifications']"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", specs_heading)
            time.sleep(2)

            # Find specifications container - try multiple XPaths
            specs_container = None
            container_xpaths = [
                "//h3[contains(text(), 'Specifications')]/parent::div/following-sibling::ul",
                "//h3[contains(text(), 'Specifications')]/following-sibling::ul",
                "//h3[contains(text(), 'Specifications')]/../following-sibling::div//ul",
                "//h3[contains(text(), 'Specifications')]/ancestor::div[1]/following-sibling::ul"
            ]

            for xpath in container_xpaths:
                try:
                    specs_container = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    self.logger.info(f"Found specs container with xpath: {xpath}")
                    break
                except:
                    continue

            if not specs_container:
                self.logger.error("Could not find specifications container")
                return all_specs

            # Find all specification sections
            section_elements = WebDriverWait(specs_container, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "./div/li"))
            )

            self.logger.info(f"Found {len(section_elements)} specification sections")

            for section_index, section in enumerate(section_elements):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section)
                    time.sleep(1)

                    # Get category name
                    try:
                        category_elem = section.find_element(By.XPATH, ".//p[contains(@class, 'o-jq')]")
                        category = category_elem.text.strip()
                        self.logger.info(f"Processing spec section {section_index+1}: {category}")
                    except:
                        category = f"Spec Section {section_index+1}"

                    # Find content div
                    try:
                        content_div = section.find_element(By.XPATH, ".//div[contains(@class, 'kgwwPb')]")
                        aria_hidden = content_div.get_attribute("aria-hidden")

                        # Expand if collapsed
                        if aria_hidden == "true":
                            try:
                                toggle_btn = section.find_element(By.XPATH, ".//div[contains(@class, 'o-f7')] | .//div[@role='button']")
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggle_btn)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", toggle_btn)
                                time.sleep(2)
                                content_div = section.find_element(By.XPATH, ".//div[contains(@class, 'kgwwPb')]")
                            except Exception as e:
                                self.logger.error(f"Error expanding spec section '{category}': {e}")

                        # Force visibility
                        driver.execute_script("""
                            arguments[0].style.height = 'auto';
                            arguments[0].style.overflow = 'visible';
                            arguments[0].setAttribute('aria-hidden', 'false');
                        """, content_div)

                        # Extract specification rows - try multiple XPaths
                        try:
                            # Try different XPaths to find rows
                            rows = []
                            row_xpaths = [
                                ".//div[contains(@class, 'o-aE')]",
                                ".//div[@class and contains(@class, 'o-f')]",
                                "./div//div[contains(@class, 'o-jK')]/..",
                                ".//div[.//div[contains(@class, 'o-jK')] and .//div[contains(@class, 'o-jJ')]]"
                            ]

                            for row_xpath in row_xpaths:
                                rows = content_div.find_elements(By.XPATH, row_xpath)
                                if len(rows) > 0:
                                    self.logger.info(f"Found {len(rows)} spec rows in '{category}' using xpath: {row_xpath}")
                                    break

                            if len(rows) == 0:
                                self.logger.warning(f"No spec rows found in '{category}' with any xpath")

                            for row in rows:
                                try:
                                    title_elem = row.find_element(By.XPATH, ".//div[contains(@class, 'o-jK')]")
                                    value_elem = row.find_element(By.XPATH, ".//div[contains(@class, 'o-jJ')]")

                                    title = title_elem.text.strip()
                                    value = value_elem.text.strip()

                                    if title and value:
                                        all_specs.append({
                                            "modelName": model_name,
                                            "makeYear": 2025,
                                            "variantName": variant_name,
                                            "specificationCategoryName": category,
                                            "specificationName": title,
                                            "specificationValue": value,
                                        })
                                except Exception as e:
                                    self.logger.debug(f"Error extracting spec row: {e}")
                                    continue
                        except Exception as e:
                            self.logger.error(f"Error extracting spec rows: {e}")
                    except Exception as e:
                        self.logger.error(f"Error with spec content div: {e}")
                except Exception as e:
                    self.logger.error(f"Error processing spec section {section_index}: {e}")

            self.logger.info(f"Total specifications extracted: {len(all_specs)}")

        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract specifications: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return all_specs

    def extract_features(self, driver, model_name, variant_name):
        """Extract features data from the page"""
        all_features = []

        try:
            # Find Features heading
            features_heading = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Features')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", features_heading)
            time.sleep(2)

            # Find features container - try multiple approaches
            features_container = None
            section_elements = []

            try:
                # Method 1: Standard structure
                features_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h3[contains(text(), 'Features')]/parent::div/following-sibling::ul"))
                )
                section_elements = features_container.find_elements(By.XPATH, "./div/li")
                self.logger.info(f"Method 1: Found {len(section_elements)} feature sections using standard structure")
            except:
                self.logger.warning("Method 1 failed, trying alternative approach")

            # Method 2: If Method 1 didn't find enough sections, try alternative
            if len(section_elements) == 0:
                try:
                    features_container = driver.find_element(By.XPATH, "//h3[contains(text(), 'Features')]/following-sibling::*[1]")
                    section_elements = features_container.find_elements(By.XPATH, ".//li[.//p[contains(@class, 'o-jq')]]")
                    self.logger.info(f"Method 2: Found {len(section_elements)} feature sections using alternative structure")
                except:
                    self.logger.error("Method 2 also failed")

            # Method 3: Direct search for all feature sections
            if len(section_elements) == 0:
                try:
                    section_elements = driver.find_elements(By.XPATH, "//h3[contains(text(), 'Features')]/following-sibling::*//li[.//p[contains(@class, 'o-jq')]]")
                    self.logger.info(f"Method 3: Found {len(section_elements)} feature sections using direct search")
                except:
                    self.logger.error("Method 3 also failed")

            if len(section_elements) == 0:
                self.logger.error("No feature sections found with any method")
                return all_features

            self.logger.info(f"Total feature sections detected: {len(section_elements)}")

            # Log all section names for debugging
            section_names = []
            for idx, section in enumerate(section_elements):
                try:
                    cat_elem = section.find_element(By.XPATH, ".//p[contains(@class, 'o-jq')]")
                    section_names.append(cat_elem.text.strip())
                except:
                    section_names.append(f"Unknown Section {idx+1}")
            self.logger.info(f"Feature sections found: {', '.join(section_names)}")

            for section_index, section in enumerate(section_elements):
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section)
                    time.sleep(1)

                    # Get category name
                    category = None
                    try:
                        category_elem = section.find_element(By.XPATH, ".//p[contains(@class, 'o-jq')]")
                        category = category_elem.text.strip()
                    except:
                        try:
                            # Try alternative - any p tag or heading
                            category_elem = section.find_element(By.XPATH, ".//p | .//h4 | .//h5")
                            category = category_elem.text.strip()
                        except:
                            category = f"Feature Section {section_index+1}"

                    self.logger.info(f"\n{'='*60}")
                    self.logger.info(f"Processing feature section {section_index+1}/{len(section_elements)}: {category}")
                    self.logger.info(f"{'='*60}")

                    # Find content div - try multiple approaches
                    content_div = None
                    try:
                        content_div = section.find_element(By.XPATH, ".//div[contains(@class, 'kgwwPb')]")
                    except:
                        try:
                            # Alternative: find any collapsible div
                            content_div = section.find_element(By.XPATH, ".//div[@aria-hidden]")
                        except:
                            try:
                                # Last resort: find any nested div structure
                                content_div = section.find_element(By.XPATH, ".//div[.//ul]")
                            except:
                                self.logger.error(f"Could not find content div for '{category}'")

                    if not content_div:
                        self.logger.error(f"Skipping section '{category}' - no content div found")
                        continue

                    # Get current state
                    aria_hidden = content_div.get_attribute("aria-hidden")
                    self.logger.info(f"Content div aria-hidden: {aria_hidden}")

                    # Expand if collapsed
                    if aria_hidden == "true":
                        try:
                            # Try multiple selector for toggle button
                            toggle_btn = None
                            try:
                                toggle_btn = section.find_element(By.XPATH, ".//div[contains(@class, 'o-f7')]")
                            except:
                                try:
                                    toggle_btn = section.find_element(By.XPATH, ".//div[@role='button']")
                                except:
                                    try:
                                        toggle_btn = section.find_element(By.XPATH, ".//*[@role='button']")
                                    except:
                                        # Try clicking the category itself
                                        toggle_btn = section.find_element(By.XPATH, ".//p[contains(@class, 'o-jq')]")

                            if toggle_btn:
                                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggle_btn)
                                time.sleep(0.5)
                                driver.execute_script("arguments[0].click();", toggle_btn)
                                self.logger.info(f"Clicked toggle button for '{category}'")
                                time.sleep(2)
                                content_div = section.find_element(By.XPATH, ".//div[contains(@class, 'kgwwPb')] | .//div[@aria-hidden]")
                            else:
                                self.logger.warning(f"No toggle button found for '{category}'")
                        except Exception as e:
                            self.logger.error(f"Error expanding feature section '{category}': {e}")

                    # Force visibility
                    try:
                        driver.execute_script("""
                            arguments[0].style.height = 'auto';
                            arguments[0].style.overflow = 'visible';
                            arguments[0].setAttribute('aria-hidden', 'false');
                        """, content_div)
                        self.logger.info(f"Forced visibility for '{category}'")
                    except Exception as e:
                        self.logger.warning(f"Could not force visibility for '{category}': {e}")

                    # Extract feature rows - try multiple approaches
                    row_items = []
                    try:
                        # First approach: standard structure
                        inner_div = content_div.find_element(By.XPATH, "./div")
                        inner_ul = inner_div.find_element(By.XPATH, "./ul")
                        row_items = inner_ul.find_elements(By.XPATH, "./li")
                    except:
                        # Fallback: try direct li elements
                        try:
                            row_items = content_div.find_elements(By.XPATH, ".//li")
                        except:
                            self.logger.error(f"Could not find row items in '{category}'")

                    self.logger.info(f"Found {len(row_items)} feature rows in '{category}'")

                    for row_idx, row_item in enumerate(row_items):
                        try:
                            # Try multiple ways to extract title and value
                            title = None
                            value = None

                            # Method 1: Standard data-itemid structure
                            try:
                                item_div = row_item.find_element(By.XPATH, "./div[@data-itemid]")
                                data_div = item_div.find_element(By.XPATH, "./div")

                                title_div = data_div.find_element(By.XPATH, ".//div[contains(@class, 'o-jK')]")
                                title = title_div.text.strip()

                                try:
                                    value_div = data_div.find_element(By.XPATH, ".//div[contains(@class, 'o-jJ')]")
                                    value = value_div.text.strip()
                                except:
                                    value = "Yes"
                            except:
                                pass

                            # Method 2: Direct div structure without data-itemid
                            if not title:
                                try:
                                    # Try finding title and value divs directly
                                    title_div = row_item.find_element(By.XPATH, ".//div[contains(@class, 'o-jK')]")
                                    title = title_div.text.strip()

                                    try:
                                        value_div = row_item.find_element(By.XPATH, ".//div[contains(@class, 'o-jJ')]")
                                        value = value_div.text.strip()
                                    except:
                                        value = "Yes"
                                except:
                                    pass

                            # Method 3: Any div structure
                            if not title:
                                try:
                                    all_divs = row_item.find_elements(By.XPATH, ".//div")
                                    for div in all_divs:
                                        div_text = div.text.strip()
                                        div_class = div.get_attribute("class") or ""

                                        if "o-jK" in div_class and div_text:
                                            title = div_text
                                        elif "o-jJ" in div_class and div_text:
                                            value = div_text

                                    if not value and title:
                                        value = "Yes"
                                except:
                                    pass

                            # Method 4: Fallback - get all text from row
                            if not title:
                                try:
                                    row_text = row_item.text.strip()
                                    if row_text:
                                        # Try to split title and value
                                        lines = row_text.split('\n')
                                        if len(lines) >= 2:
                                            title = lines[0].strip()
                                            value = lines[1].strip()
                                        elif len(lines) == 1:
                                            title = lines[0].strip()
                                            value = "Yes"
                                except:
                                    pass

                            if title:
                                if not value or value == "":
                                    value = "Yes"

                                all_features.append({
                                    "modelName": model_name,
                                    "makeYear": 2025,
                                    "variantName": variant_name,
                                    "featureCategoryName": category,
                                    "featureName": title,
                                    "featureValue": value,
                                    "featureIsHighlighted": "",
                                })
                                self.logger.debug(f"Extracted feature: {title} = {value}")
                            else:
                                self.logger.warning(f"Could not extract title from row {row_idx} in '{category}'")

                        except Exception as e:
                            self.logger.error(f"Error extracting row {row_idx} in '{category}': {e}")
                            continue

                except Exception as e:
                    self.logger.error(f"Error processing feature section {section_index}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())

            self.logger.info(f"Total features extracted: {len(all_features)}")

        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract features: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return all_features
