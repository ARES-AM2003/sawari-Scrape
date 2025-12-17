import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time


class VariantsSpider(scrapy.Spider):
    name = "variants"
    allowed_domains = ["cardekho.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_variants = set()  # Track variants to prevent duplicates

        # Accept URL from command line argument (single URL)
        url = kwargs.get('url')
        if url:
            self.start_urls = [url]
            self.logger.info(f"Using single URL from command line: {url}")
        
        # Accept URLs from file (for batch processing with single browser + tabs)
        urls_file = kwargs.get('urls_file')
        if urls_file:
            import os
            if os.path.exists(urls_file):
                with open(urls_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                self.start_urls = urls
                self.logger.info(f"✅ Loaded {len(urls)} URLs from file: {urls_file}")
                self.logger.info(f"💡 Will use single browser with multiple tabs for parallel processing!")
            else:
                self.logger.error(f"❌ URLs file not found: {urls_file}")

    start_urls = [
        "https://www.cardekho.com/overview/Citroen_C3/Citroen_C3_X_Shine_Dual_Tone_CNG.htm",
    #"https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Delta.htm",
    #"https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Delta_AMT.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Delta_Dual_Tone_AMT.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Zeta.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Zeta_Dual_Tone.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Zeta_AMT.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Zeta_Dual_Tone_AMT.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Alpha.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Alpha_Dual_Tone.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Alpha_AMT.htm",
    # "https://www.cardekho.com/overview/Maruti_Ignis/Maruti_Ignis_Alpha_Dual_Tone_AMT.htm",
    ]

    custom_settings = {
        # Note: CONCURRENT_REQUESTS_PER_DOMAIN and SELENIUM_MAX_TABS will be set via command line
        # when using the run_variants_parallel.py script for optimal multi-tab performance
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.RFPDupeFilter',  # Enable duplicate filtering
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.VariantInfoCsvPipeline': 800,
        }
    }

    def start_requests(self):
        for index, url in enumerate(self.start_urls, 1):
            self.logger.info(f"Processing URL {index}/{len(self.start_urls)}: {url}")
            yield SeleniumRequest(
                url=url,
                callback=self.parse,
                wait_time=20,
                screenshot=True,
                # Removed dont_filter=True to enable Scrapy's built-in duplicate filtering
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

        # Initialize all fields with default values
        model_name = ""
        variant_name = ""
        price = ""
        fuel_type = ""
        mileage = ""
        seating_capacity = ""

        if driver:
            self.logger.info(f"[LOG] WebDriver initialized: {driver.session_id}")
        else:
            self.logger.error(f"[ERROR] WebDriver not found in response.meta for URL: {current_url}")
            return

        print(f"[LOG] WebDriver found in response.meta: {driver}")
        print(f"[LOG] WebDriver session ID: {driver.session_id}")

        # Extract brand and model name dynamically from h1
        try:
            nav_div = driver.find_element(By.XPATH, "//div[contains(@class, 'modelNavInner')]")
            nav_ul = nav_div.find_element(By.XPATH, ".//ul[contains(@class, 'modelNavUl')]")
            nav_lis = nav_ul.find_elements(By.TAG_NAME, "li")
            model_name = nav_lis[0].find_element(By.TAG_NAME, "a").text.strip()
            variant_name = nav_lis[1].find_element(By.TAG_NAME, "a").text.strip()
            self.logger.info(f"Extracted - Model: {model_name}, Variant: {variant_name}")
            open("car_info_debug.txt", "a", encoding="utf-8").write(
                f"URL {url_index}/{total_urls} - Model: {model_name}, Variant: {variant_name}\n"
            )
        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract nav info: {e}")

        # Extract price from the price section
        try:
            price_elem = driver.find_element(By.XPATH, "//div[contains(@class, 'price')]")
            price_html = price_elem.get_attribute("innerHTML")
            match = re.search(r'</i>\s*([^<]+)', price_html)
            if match:
                price = match.group(1).strip()
            else:
                price = ""
            self.logger.info(f"Extracted price: {price}")
            open("car_info_debug.txt", "a", encoding="utf-8").write(f"Price: {price}\n")
        except Exception as e:
            price = ""
            self.logger.error(f"[ERROR] Could not extract price: {e}")

        # Scroll to specification section and extract details
        try:
            specs_heading = driver.find_element(By.XPATH, "//h2[contains(@class, 'plr-20') and contains(text(), 'specifications')]")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", specs_heading)
            time.sleep(1)

            li_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'specsSticky')]//ul/li")

            if len(li_elements) < 4:
                self.logger.error(f"[ERROR] Expected at least 4 tabs, found {len(li_elements)}")
            else:
                second_li = li_elements[1]
                fourth_li = li_elements[3]

                # Click second tab (Fuel & Performance)
                try:
                    second_li.find_element(By.TAG_NAME, "a").click()
                    time.sleep(2)
                    self.logger.info("Clicked on Fuel & Performance tab")
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not click second tab: {e}")

                # Fuel & Performance Table
                try:
                    fuel_perf_table = driver.find_element(
                        By.XPATH,
                        "//h3[@id='Fuel&Performance']/following-sibling::table[1]"
                    )
                    # Fuel Type
                    try:
                        fuel_type_elem = fuel_perf_table.find_element(
                            By.XPATH,
                            ".//tr[td[contains(text(), 'Fuel Type')]]/td[2]/span"
                        )
                        fuel_type = fuel_type_elem.text.strip()
                        self.logger.info(f"Extracted fuel type: {fuel_type}")
                    except Exception as e:
                        fuel_type = ""
                        self.logger.error(f"[ERROR] Could not extract fuel type: {e}")

                    # Mileage
                    try:
                        mileage_elem = fuel_perf_table.find_element(
                            By.XPATH,
                            ".//tr[td[contains(text(), 'Petrol Mileage ARAI')]]/td[2]/span"
                        )
                        mileage = mileage_elem.text.strip()
                        self.logger.info(f"Extracted mileage: {mileage}")
                    except Exception as e:
                        mileage = ""
                        self.logger.error(f"[ERROR] Could not extract mileage: {e}")

                    open("car_info_debug.txt", "a", encoding="utf-8").write(
                        f"Fuel Type: {fuel_type}, Petrol Mileage ARAI: {mileage}\n"
                    )
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not extract Fuel & Performance table: {e}")

                # Click on the fourth tab (Dimensions & Capacity)
                try:
                    fourth_li.find_element(By.TAG_NAME, "a").click()
                    time.sleep(2)
                    self.logger.info("Clicked on Dimensions & Capacity tab")
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not click fourth tab: {e}")

                # Dimensions & Capacity Table
                try:
                    dimensions_table = driver.find_element(
                        By.XPATH,
                        "//h3[@id='Dimensions&Capacity']/following-sibling::table[1]"
                    )
                    # Seating Capacity
                    try:
                        seating_capacity_element = dimensions_table.find_element(
                            By.XPATH,
                            ".//tr[td[span[contains(text(), 'Seating Capacity')]]]/td[2]/span"
                        )
                        seating_capacity = seating_capacity_element.text.strip()
                        self.logger.info(f"Extracted seating capacity: {seating_capacity}")
                    except Exception as e:
                        seating_capacity = ""
                        self.logger.error(f"[ERROR] Could not extract seating capacity: {e}")

                    open("car_info_debug.txt", "a", encoding="utf-8").write(
                        f"Seating Capacity: {seating_capacity}\n"
                    )
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not extract Dimensions & Capacity table: {e}")

                # Debug log for tab names
                try:
                    second_text = second_li.text.strip()
                    fourth_text = fourth_li.text.strip()
                    open("car_info_debug.txt", "a", encoding="utf-8").write(
                        f"Second Item: {second_text}, Fourth Item: {fourth_text}\n"
                    )
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not log tab names: {e}")

        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract specifications: {e}")

        # Log completion
        self.logger.info(f"Completed processing URL {url_index}/{total_urls}: {current_url}")
        open("car_info_debug.txt", "a", encoding="utf-8").write(f"{'-' * 80}\n")

        # Create unique identifier for this variant
        variant_key = (model_name, variant_name)

        # Only yield if we haven't seen this variant before
        if variant_key not in self.seen_variants:
            self.seen_variants.add(variant_key)
            self.logger.info(f"✓ Yielding NEW variant: {variant_name}")

            yield {
                "modelName": model_name,
                "makeYear": 2025,
                "variantName": variant_name,
                "variantPrice": price,
                "variantFuelType": fuel_type,
                "variantSeatingCapacity": seating_capacity,
                "variantType": " ",
                "variantIsPopular": " ",
                "variantMileage": mileage,
            }
        else:
            self.logger.warning(f"✗ SKIPPED DUPLICATE variant: {variant_name}")
