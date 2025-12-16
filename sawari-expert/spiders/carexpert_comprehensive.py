import re
import time

import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CarexpertComprehensiveSpider(scrapy.Spider):
    """
    Comprehensive spider for CarExpert website
    Scrapes: Models, Variants, FAQs, and Pros/Cons
    Example URL: https://www.carexpert.com.au/mg/mg-s5-ev
    """

    name = "carexpert_comprehensive"
    allowed_domains = ["carexpert.com.au"]

    def __init__(self, start_url=None, *args, **kwargs):
        super(CarexpertComprehensiveSpider, self).__init__(*args, **kwargs)

        if start_url:
            self.start_urls = [start_url]
        else:
            # Default URL
            self.start_urls = ["https://www.carexpert.com.au/mg/mg-s5-ev"]

        # Extract brand and model from URL for pipeline
        url = self.start_urls[0]
        url_parts = url.rstrip("/").split("/")

        if len(url_parts) >= 2:
            self.brand_name = (
                url_parts[-2].upper() if len(url_parts) >= 2 else "Unknown"
            )
            self.model_name = (
                url_parts[-1].replace("-", " ").upper()
                if len(url_parts) >= 1
                else "Unknown"
            )
        else:
            self.brand_name = "MG"
            self.model_name = "Hs"

        self.logger.info(f"Initialized spider for: {self.brand_name} {self.model_name}")

    custom_settings = {
        "ITEM_PIPELINES": {
            "sawari-expert.pipelines.ModelInfoCsvPipeline": 100,
            "sawari-expert.pipelines.VariantInfoCsvPipeline": 200,
            "sawari-expert.pipelines.FaqInfoCsvPipeline": 300,
            "sawari-expert.pipelines.ProsConsInfoCsvPipeline": 400,
        },
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 2,
    }

    def start_requests(self):
        yield SeleniumRequest(
            url=self.start_urls[0],
            callback=self.parse,
            wait_time=20,
            screenshot=True,
            dont_filter=True,
            meta={"dont_cache": True},
        )

    def parse(self, response):
        driver = response.meta.get("driver")

        if not driver:
            self.logger.error("[ERROR] WebDriver not found in response.meta")
            return

        self.logger.info(f"[LOG] WebDriver initialized: {driver.session_id}")

        # Wait for page to load
        time.sleep(3)

        # Scroll through the page to ensure all content loads
        self.logger.info("Scrolling through page to load all content...")
        self.scroll_page(driver)

        # Extract all data
        for item in self.extract_model_info(driver):
            yield item

        for item in self.extract_variants(driver):
            yield item

        for item in self.extract_faqs(driver):
            yield item

        for item in self.extract_pros_cons(driver):
            yield item

        self.logger.info("✓ Completed scraping all data from CarExpert")

    def scroll_page(self, driver):
        """Scroll through the page to ensure all dynamic content loads"""
        try:
            # Get initial page height
            last_height = driver.execute_script("return document.body.scrollHeight")

            # Scroll in increments
            scroll_pause_time = 1
            scroll_increment = 800

            current_position = 0
            max_scrolls = 10  # Prevent infinite scrolling
            scroll_count = 0

            while scroll_count < max_scrolls:
                # Scroll down by increment
                current_position += scroll_increment
                driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(scroll_pause_time)

                # Check if we've reached the bottom
                new_height = driver.execute_script("return document.body.scrollHeight")
                if current_position >= new_height:
                    break

                scroll_count += 1

            # Scroll back to top
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.logger.info(f"✓ Completed page scroll ({scroll_count} scrolls)")

        except Exception as e:
            self.logger.warning(f"Error during page scroll: {e}")

    def extract_model_info(self, driver):
        """Extract model information from the hero section"""
        self.logger.info("=" * 80)
        self.logger.info("EXTRACTING MODEL INFORMATION")
        self.logger.info("=" * 80)

        model_items = []

        try:
            # Extract model name from h1
            try:
                model_h1 = driver.find_element(
                    By.XPATH, "//h1[contains(@class, '_19m0jur1v')]"
                )
                model_name = model_h1.text.strip()
                self.logger.info(f"Extracted model name: {model_name}")
            except:
                model_name = self.model_name
                self.logger.warning(
                    f"Could not extract model name from page, using: {model_name}"
                )

            # Extract description
            try:
                description_elem = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class, '_19m0jurb')]//p[contains(@class, 'm7p3v71')]",
                )
                description = description_elem.text.strip()
                self.logger.info(f"Extracted description: {description[:100]}...")
            except:
                description = ""
                self.logger.warning("Could not extract model description")

            # Extract retail price
            try:
                price_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Retail Price']]/p[@class='_1ivmml50']",
                )
                retail_price = price_elem.text.strip()
                self.logger.info(f"Extracted retail price: {retail_price}")
            except:
                retail_price = ""
                self.logger.warning("Could not extract retail price")

            # Extract transmission
            try:
                transmission_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Transmission']]/p[@class='_1ivmml50']",
                )
                transmission = transmission_elem.text.strip()
                self.logger.info(f"Extracted transmission: {transmission}")
            except:
                transmission = ""
                self.logger.warning("Could not extract transmission")

            # Extract driven wheels
            try:
                driven_wheels_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Driven Wheels']]/p[@class='_1ivmml50']",
                )
                driven_wheels = driven_wheels_elem.text.strip()
                self.logger.info(f"Extracted driven wheels: {driven_wheels}")
            except:
                driven_wheels = ""
                self.logger.warning("Could not extract driven wheels")

            # Extract fuel type
            try:
                fuel_type_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Fuel Type']]/p[@class='_1ivmml50']",
                )
                fuel_type = fuel_type_elem.text.strip()
                self.logger.info(f"Extracted fuel type: {fuel_type}")
            except:
                fuel_type = ""
                self.logger.warning("Could not extract fuel type")

            # Extract body type
            try:
                body_type_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Body Types']]/p[@class='_1ivmml50']",
                )
                body_type = body_type_elem.text.strip()
                self.logger.info(f"Extracted body type: {body_type}")
            except:
                body_type = ""
                self.logger.warning("Could not extract body type")

            # Extract powertrain type
            try:
                powertrain_elem = driver.find_element(
                    By.XPATH,
                    "//div[@id='vehicle-spec']//div[p[text()='Powertrain Type']]/p[@class='_1ivmml50']",
                )
                powertrain = powertrain_elem.text.strip()
                self.logger.info(f"Extracted powertrain: {powertrain}")
            except:
                powertrain = ""
                self.logger.warning("Could not extract powertrain")

            # Create model item
            model_item = {
                "brandName": self.brand_name,
                "modelName": model_name,
                "modelDescription": description,
                "modelTagline": "",
                "modelIsHiglighted": "",
                "bodyType": body_type,
            }

            model_items.append(model_item)
            self.logger.info(f"✓ Successfully extracted model information")

        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting model info: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_model_info.png")

        return model_items

    def extract_variants(self, driver):
        """Extract variant information from the variants section"""
        self.logger.info("=" * 80)
        self.logger.info("EXTRACTING VARIANT INFORMATION")
        self.logger.info("=" * 80)

        variant_items = []

        try:
            # Scroll to variants section
            variants_heading_found = False
            try:
                variants_heading = driver.find_element(
                    By.XPATH, "//h2[contains(text(), 'Available Variants')]"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    variants_heading,
                )
                time.sleep(2)
                variants_heading_found = True
                self.logger.info("✓ Found and scrolled to 'Available Variants' heading")
            except:
                self.logger.warning(
                    "Could not find 'Available Variants' heading, trying alternative methods"
                )

                # Try to find variant section by looking for variant links first
                try:
                    first_variant_link = driver.find_element(
                        By.XPATH, "//a[contains(@href, '/features-and-specs')]"
                    )
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        first_variant_link,
                    )
                    time.sleep(2)
                    self.logger.info("✓ Found variant section via variant link")
                    variants_heading_found = True
                except:
                    self.logger.warning("Could not find variant section")

            # Take screenshot for debugging
            driver.save_screenshot("variants_section.png")

            # Save page source for debugging
            try:
                with open(
                    "debug_variants_page_source.html", "w", encoding="utf-8"
                ) as f:
                    f.write(driver.page_source)
                self.logger.info("Saved page source to debug_variants_page_source.html")
            except Exception as e:
                self.logger.warning(f"Could not save page source: {e}")

            # Find all variant links - using the correct class from the HTML
            # Looking for: <a target="_self" href="/mg/mg-s5-ev/excite/features-and-specs" class="_2mb3ted _1ivmml51f _18bmbcy6">
            variant_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@class, '_2mb3ted') and contains(@class, '_18bmbcy6')]",
            )

            self.logger.info(
                f"Found {len(variant_links)} variant links with primary selector"
            )

            if len(variant_links) == 0:
                # Try alternative selector - just look for links to features-and-specs
                self.logger.info("Trying alternative selector 1...")
                variant_links = driver.find_elements(
                    By.XPATH,
                    "//a[@target='_self' and contains(@href, '/features-and-specs')]",
                )
                self.logger.info(
                    f"Found {len(variant_links)} variant links using alternative selector 1"
                )

            if len(variant_links) == 0:
                # Try another alternative - look for any link with features-and-specs
                self.logger.info("Trying alternative selector 2...")
                variant_links = driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, '/features-and-specs')]",
                )
                self.logger.info(
                    f"Found {len(variant_links)} variant links using alternative selector 2"
                )

            if len(variant_links) == 0:
                # Try to find by the div structure
                self.logger.info("Trying alternative selector 3 (by div structure)...")
                variant_links = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, '_2mb3te1')]//ancestor::a",
                )
                self.logger.info(
                    f"Found {len(variant_links)} variant links using alternative selector 3"
                )

            for idx, variant_link in enumerate(variant_links):
                try:
                    # Scroll to variant
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        variant_link,
                    )
                    time.sleep(0.5)

                    # Extract variant name from h2 tag
                    # Looking for: <h2 class="_2mb3te8 _1ivmml5i0 _1ivmml5w4 _1ivmml5ul _1ivmml56 _1ivmml5i _1ivmml5413 _1ivmml5s _1ivmml5134">Excite</h2>
                    try:
                        variant_name_elem = variant_link.find_element(
                            By.XPATH, ".//h2[contains(@class, '_2mb3te8')]"
                        )
                        variant_name = variant_name_elem.text.strip()
                        self.logger.info(f"Variant {idx + 1}: {variant_name}")
                    except Exception as e:
                        # Try alternative - just get any h2
                        try:
                            variant_name_elem = variant_link.find_element(
                                By.XPATH, ".//h2"
                            )
                            variant_name = variant_name_elem.text.strip()
                            self.logger.info(
                                f"Variant {idx + 1} (alt method): {variant_name}"
                            )
                        except:
                            variant_name = ""
                            self.logger.warning(
                                f"Could not extract variant name for variant {idx + 1}: {e}"
                            )

                    # Extract variant price
                    # Looking for: <div class="_1ivmml5i _1ivmml55 _1ivmml5fz _1ivmml510s _1ivmml51op _1ivmml5zm _1ivmml5125 _1ivmml5ur _1ivmml5r _18bmbcy4 _1ivmml51e7 _1ivmml5hy _1ivmml5i _1ivmml52 _1ivmml5ur">Price from $0
                    try:
                        price_elem = variant_link.find_element(
                            By.XPATH, ".//div[contains(@class, '_18bmbcy4')]"
                        )
                        price_text = price_elem.text.strip()
                        # Clean price text (remove "Price from " prefix if present)
                        price = re.sub(r"Price from\s*", "", price_text).strip()
                        # Remove the † symbol if present
                        price = re.sub(r"†", "", price).strip()
                        self.logger.info(f"Variant price: {price}")
                    except Exception as e:
                        # Try to find any div with price text
                        try:
                            price_elem = variant_link.find_element(
                                By.XPATH,
                                ".//div[contains(text(), 'Price from') or contains(text(), '$')]",
                            )
                            price_text = price_elem.text.strip()
                            price = re.sub(r"Price from\s*", "", price_text).strip()
                            price = re.sub(r"†", "", price).strip()
                            self.logger.info(f"Variant price (alt method): {price}")
                        except:
                            price = ""
                            self.logger.warning(
                                f"Could not extract price for variant {idx + 1}: {e}"
                            )

                    # Extract variant link
                    try:
                        variant_url = variant_link.get_attribute("href")
                        self.logger.info(f"Variant URL: {variant_url}")
                    except:
                        variant_url = ""
                        self.logger.warning(
                            f"Could not extract URL for variant {idx + 1}"
                        )

                    # Only add variant if we have at least a name
                    if variant_name:
                        # Create variant item
                        variant_item = {
                            "modelName": f"{self.brand_name} {self.model_name}",
                            "makeYear": 2025,
                            "variantName": variant_name,
                            "variantPrice": price,
                            "variantFuelType": "",
                            "variantSeatingCapacity": "",
                            "variantType": "",
                            "variantIsPopular": "",
                            "variantMileage": "",
                        }

                        variant_items.append(variant_item)
                        self.logger.info(f"✓ Added variant: {variant_name} - {price}")
                    else:
                        self.logger.warning(
                            f"Skipped variant {idx + 1} - no name found"
                        )

                except Exception as e:
                    self.logger.error(f"Error extracting variant {idx + 1}: {e}")
                    import traceback

                    self.logger.error(traceback.format_exc())
                    continue

            self.logger.info(f"✓ Successfully extracted {len(variant_items)} variants")

        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting variants: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_variants.png")

        return variant_items

    def extract_faqs(self, driver):
        """Extract FAQ information from the FAQ section"""
        self.logger.info("=" * 80)
        self.logger.info("EXTRACTING FAQ INFORMATION")
        self.logger.info("=" * 80)

        faq_items = []

        try:
            # Scroll to FAQ section
            try:
                faq_heading = driver.find_element(
                    By.XPATH, "//h2[contains(text(), 'Frequently Asked Questions')]"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    faq_heading,
                )
                time.sleep(2)
                self.logger.info("Scrolled to FAQ section")
            except:
                self.logger.warning("Could not find FAQ heading")
                return faq_items

            # Take screenshot
            driver.save_screenshot("faq_section_carexpert.png")

            # Find all FAQ accordion elements
            accordion_elements = driver.find_elements(
                By.XPATH, "//div[@data-testid='accordion']"
            )

            self.logger.info(f"Found {len(accordion_elements)} FAQ accordion elements")

            for idx, accordion_elem in enumerate(accordion_elements):
                try:
                    # Scroll to accordion
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        accordion_elem,
                    )
                    time.sleep(0.5)

                    # Find question button
                    try:
                        question_button = accordion_elem.find_element(
                            By.XPATH,
                            ".//button[@data-testid='accordion-header-button']",
                        )
                    except:
                        question_button = accordion_elem.find_element(
                            By.XPATH, ".//button"
                        )

                    # Get question text
                    try:
                        question_elem = accordion_elem.find_element(
                            By.XPATH,
                            ".//span[@data-testid='accordion-header-title-text']",
                        )
                        question_text = question_elem.text.strip()
                    except:
                        question_text = question_button.text.strip()

                    self.logger.info(f"FAQ {idx + 1} Question: {question_text[:60]}...")

                    # Check if accordion is expanded
                    is_expanded = (
                        question_button.get_attribute("aria-expanded") == "true"
                    )

                    # Click to expand if not expanded
                    if not is_expanded:
                        try:
                            driver.execute_script(
                                "arguments[0].click();", question_button
                            )
                            time.sleep(1)
                            self.logger.info(f"Expanded accordion {idx + 1}")
                        except:
                            self.logger.warning(f"Could not expand accordion {idx + 1}")
                            continue

                    # Extract answer
                    answer_text = ""
                    try:
                        content_div = accordion_elem.find_element(
                            By.XPATH, ".//div[@data-testid='accordion-content']"
                        )

                        # Try to find paragraph
                        try:
                            answer_elem = content_div.find_element(
                                By.XPATH, ".//p[contains(@class, 'm7p3v71')]"
                            )
                            answer_text = answer_elem.text.strip()
                        except:
                            answer_text = content_div.text.strip()

                        self.logger.info(f"FAQ {idx + 1} Answer: {answer_text[:60]}...")

                    except Exception as e:
                        self.logger.error(
                            f"Error extracting answer for FAQ {idx + 1}: {e}"
                        )
                        continue

                    # Create FAQ item
                    if question_text and answer_text:
                        faq_item = {
                            "modelName": f"{self.brand_name} {self.model_name}",
                            "faqQuestion": question_text,
                            "faqAnswer": answer_text,
                        }
                        faq_items.append(faq_item)
                        self.logger.info(f"✓ Extracted FAQ {idx + 1}")

                except Exception as e:
                    self.logger.error(f"Error processing FAQ {idx + 1}: {e}")
                    continue

            self.logger.info(f"✓ Successfully extracted {len(faq_items)} FAQs")

        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting FAQs: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_faqs.png")

        return faq_items

    def extract_pros_cons(self, driver):
        """Extract pros and cons information"""
        self.logger.info("=" * 80)
        self.logger.info("EXTRACTING PROS AND CONS")
        self.logger.info("=" * 80)

        pros_cons_items = []

        try:
            # Scroll down to find pros/cons section
            # Try multiple times to find the section
            pros_cons_found = False

            # Method 1: Look for h3 with "Pros" and "Cons"
            try:
                pros_heading = driver.find_element(
                    By.XPATH, "//h3[contains(text(), 'Pros')]"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    pros_heading,
                )
                time.sleep(2)
                pros_cons_found = True
                self.logger.info("Found pros/cons section using h3 headings")
            except:
                self.logger.info(
                    "Could not find pros/cons with h3, trying alternative methods"
                )

            # Method 2: Look for SVG icons (cross and minus)
            if not pros_cons_found:
                try:
                    # Look for the specific div structure with SVG icons
                    pros_div = driver.find_element(
                        By.XPATH, "//div[contains(@class, '_6h1tsc8')]/.."
                    )
                    driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                        pros_div,
                    )
                    time.sleep(2)
                    pros_cons_found = True
                    self.logger.info("Found pros/cons section using SVG icons")
                except:
                    self.logger.warning("Could not find pros/cons section")
                    return pros_cons_items

            # Take screenshot
            driver.save_screenshot("pros_cons_section.png")

            # Extract Pros
            try:
                # Find the pros container using the h3 or SVG structure
                pros_containers = driver.find_elements(
                    By.XPATH,
                    "//div[.//h3[contains(text(), 'Pros')]]//ul[contains(@class, '_6h1tsc2')]",
                )

                if not pros_containers:
                    # Alternative: look for ul directly
                    pros_containers = driver.find_elements(
                        By.XPATH,
                        "//ul[contains(@class, '_6h1tsc2')][preceding-sibling::div//h3[contains(text(), 'Pros')]]",
                    )

                for pros_container in pros_containers:
                    pros_list = pros_container.find_elements(
                        By.XPATH, ".//li[contains(@class, '_6h1tsc4')]"
                    )

                    for pro_item in pros_list:
                        pro_text = pro_item.text.strip()
                        if pro_text:
                            pros_cons_items.append(
                                {
                                    "modelName": f"{self.brand_name} {self.model_name}",
                                    "prosConsType": "Pro",
                                    "prosConsContent": pro_text,
                                }
                            )
                            self.logger.info(f"✓ Extracted Pro: {pro_text}")

                self.logger.info(
                    f"Extracted {len([p for p in pros_cons_items if p['prosConsType'] == 'Pro'])} pros"
                )

            except Exception as e:
                self.logger.error(f"Error extracting pros: {e}")

            # Extract Cons
            try:
                # Find the cons container
                cons_containers = driver.find_elements(
                    By.XPATH,
                    "//div[.//h3[contains(text(), 'Cons')]]//ul[contains(@class, '_6h1tsc2')]",
                )

                if not cons_containers:
                    # Alternative: look for ul directly
                    cons_containers = driver.find_elements(
                        By.XPATH,
                        "//ul[contains(@class, '_6h1tsc2')][preceding-sibling::div//h3[contains(text(), 'Cons')]]",
                    )

                for cons_container in cons_containers:
                    cons_list = cons_container.find_elements(
                        By.XPATH, ".//li[contains(@class, '_6h1tsc4')]"
                    )

                    for con_item in cons_list:
                        con_text = con_item.text.strip()
                        if con_text:
                            pros_cons_items.append(
                                {
                                    "modelName": f"{self.brand_name} {self.model_name}",
                                    "prosConsType": "Con",
                                    "prosConsContent": con_text,
                                }
                            )
                            self.logger.info(f"✓ Extracted Con: {con_text}")

                self.logger.info(
                    f"Extracted {len([c for c in pros_cons_items if c['prosConsType'] == 'Con'])} cons"
                )

            except Exception as e:
                self.logger.error(f"Error extracting cons: {e}")

            self.logger.info(
                f"✓ Successfully extracted {len(pros_cons_items)} pros/cons items"
            )

        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting pros/cons: {e}")
            import traceback

            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_pros_cons.png")

        return pros_cons_items
