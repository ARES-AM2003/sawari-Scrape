from datetime import datetime
import json
import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
import os


class ProsConsColoursSpider(scrapy.Spider):
    name = "pros_cons_colours"
    allowed_domains = ["cardekho.com"]
    start_urls = ["https://www.cardekho.com/carmodels/Maruti/Maruti_Ciaz"]

    # Extract brand and model from start_urls

    brand_name = 'Maruti'
    model_name = 'Ciaz'

    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.ProsConsInfoJsonPipeline': 300,
            'sawari-expert.pipelines.ProsConsInfoCsvPipeline': 400,
            'sawari-expert.pipelines.ColourOptionsInfoJsonPipeline': 500,
            'sawari-expert.pipelines.ColourOptionsInfoCsvPipeline': 600,
        }
    }

    def start_requests(self):
        yield SeleniumRequest(
            url=self.start_urls[0],
            callback=self.parse,
            wait_time=20,
            screenshot=True,
            dont_filter=True,
            meta={'dont_cache': True}
        )

    def parse(self, response):
        driver = response.meta.get("driver")

        # Log to check if driver is initialized
        if driver:
            self.logger.info("[LOG] WebDriver initialized: %s", driver.session_id)
        else:
            self.logger.error("[ERROR] WebDriver not found in response.meta")
            return

        # Extract model name from h1
        try:
            model_name_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'thcHeading')]"))
            )
            full_name = model_name_elem.text.strip()

            # Extract model name (assuming format is "Brand ModelName")
            parts = full_name.split()
            if len(parts) >= 2:
                extracted_brand = parts[0]
                extracted_model = " ".join(parts[1:])
            else:
                extracted_brand = "Unknown"
                extracted_model = full_name

            # Update spider attributes with extracted data
            self.brand_name = extracted_brand
            self.model_name = extracted_model

            self.logger.info(f"Extracted brand: {extracted_brand}, model: {extracted_model}")
            model_name = extracted_model
        except Exception as e:
            model_name = ""
            self.logger.error(f"[ERROR] Could not extract model name: {e}")
            driver.save_screenshot("error_model_name.png")

        # Extract pros and cons
        pros_cons_items = self.extract_pros_cons(driver, model_name)
        for item in pros_cons_items:
            yield item

        # Now navigate to colors page
        try:
            # First find and click "More" dropdown if it's not already expanded
            try:
                more_dropdown = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[@data-dropdown-text='more' and text()='More']"))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", more_dropdown)
                time.sleep(1)
                more_dropdown.click()
                self.logger.info("Clicked on 'More' dropdown")
                time.sleep(2)
            except Exception as e:
                self.logger.error(f"Error clicking 'More' dropdown: {e}")

            # Now find and click Colors option
            try:
                colours_link = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(@class, 'loannavtab')]/span[contains(@class, 'icon-colors')]/parent::span"))
                )
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", colours_link)
                time.sleep(1)
                colours_link.click()
                self.logger.info("Clicked on 'Colours' link")
                time.sleep(5)

                # Now extract color options
                color_items = self.extract_colors(driver, model_name)
                with open(f"turi.json", "w", encoding="utf-8") as f:
                    json.dump({
                        "model_name": model_name,
                        "extraction_time": datetime.now().isoformat(),
                        "num_colors_found": len(color_items),
                        "color_data": color_items
                    }, f, indent=4)
                for item in color_items:
                    yield item

            except Exception as e:
                self.logger.error(f"Error clicking 'Colours' link: {e}")

        except Exception as e:
            self.logger.error(f"Error navigating to colors page: {e}")

    def extract_pros_cons(self, driver, model_name):
        """Extract pros and cons information"""
        pros_cons_items = []

        try:
            # Find pros and cons section by h2
            pros_cons_heading = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, f"//h2[contains(text(), 'Pros & Cons of')]"))
            )

            # Scroll to pros and cons section
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pros_cons_heading)
            time.sleep(2)

            # Take screenshot for debugging
            driver.save_screenshot("pros_cons_section.png")

            # Extract pros
            try:
                pros_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'rightthings')][.//h3[contains(text(), 'Things We Like')]]"))
                )

                pros_list = pros_container.find_elements(By.XPATH, ".//ul/li")

                for pro_item in pros_list:
                    pro_text = pro_item.text.strip()
                    if pro_text:
                        pros_cons_items.append({
                            "modelName": model_name,
                            "prosConsType": "Pro",
                            "prosConsContent": pro_text
                        })
                        self.logger.info(f"Extracted pro: {pro_text}")
            except Exception as e:
                self.logger.error(f"Error extracting pros: {e}")

            # Extract cons
            try:
                cons_container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'rightthings') and contains(@class, 'wrongthings')]"))
                )

                cons_list = cons_container.find_elements(By.XPATH, ".//ul/li")

                for con_item in cons_list:
                    con_text = con_item.text.strip()
                    if con_text:
                        pros_cons_items.append({
                            "modelName": model_name,
                            "prosConsType": "Con",
                            "prosConsContent": con_text
                        })
                        self.logger.info(f"Extracted con: {con_text}")
            except Exception as e:
                self.logger.error(f"Error extracting cons: {e}")

        except Exception as e:
            self.logger.error(f"[ERROR] Error finding pros and cons section: {e}")
            driver.save_screenshot("error_pros_cons.png")

        return pros_cons_items



    def extract_colors(self, driver, model_name):
        """Extract color options"""
        color_items = []

        try:
            # Wait for the colors page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//li[contains(@class, 'gscr_dot')]"))
            )

            # Scroll to the colour section
            try:
                # Select all color option <li> elements
                color_option_elements = driver.find_elements(
                    By.XPATH,
                    "//li[contains(@class, 'gscr_dot')]"
                )

                if color_option_elements:
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", color_option_elements[0])
                    self.logger.info(f"Found {len(color_option_elements)} color options")
                else:
                    self.logger.warning("No color options found on the page")

            except Exception as e:
                self.logger.error(f"[ERROR] Could not scroll to color options: {e}")

            # Extract color options: name and hex code
            try:
                color_option_elements = driver.find_elements(
                    By.XPATH,
                    "//li[contains(@class, 'gscr_dot')]"
                )

                for li in color_option_elements:
                    # Extract color name from <a> title
                    try:
                        color_name = li.find_element(By.XPATH, ".//a").get_attribute("title")
                        if not color_name:
                            # Try getting from text in colorTxt div that might appear when hovering
                            try:
                                color_name_div = WebDriverWait(driver, 2).until(
                                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'colorTxt')]"))
                            )
                                color_name = color_name_div.text.strip()
                            except:
                                pass
                    except Exception:
                        color_name = "Unknown Color"

                    # Extract style from <i> (coloredIcon)
                    try:
                        icon_elem = li.find_element(By.XPATH, ".//i[contains(@class, 'coloredIcon')]")
                        style = icon_elem.get_attribute("style")
                        match = re.search(r"(rgb[a]?\([^)]+\)|#[0-9a-fA-F]{3,6})", style)
                        color_hex = match.group(1) if match else ""
                    except Exception:
                        color_hex = ""

                    rgb_values = color_hex.strip().lower().replace('rgb(', '').replace(')', '').split(',')
                    r, g, b = [int(x.strip()) for x in rgb_values]
                    color_hex =  f"#{r:02X}{g:02X}{b:02X}"

                    # Add to our items list
                    color_item = {
                        "modelName": model_name,
                        "colourName": color_name,
                        "hexCode": color_hex
                    }

                    color_items.append(color_item)
                    self.logger.info(f"Extracted color: {color_name} - {color_hex}")

            except Exception as e:
                self.logger.error(f"[ERROR] Could not extract color options: {e}")

        except Exception as e:
            self.logger.error(f"[ERROR] Error in extract_colors: {e}")

        return color_items
