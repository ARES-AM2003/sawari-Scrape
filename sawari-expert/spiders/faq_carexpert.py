import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


class FaqCarexpertSpider(scrapy.Spider):
    name = "faq_carexpert"
    allowed_domains = ["carexpert.com.au"]
    start_urls = ["https://www.carexpert.com.au/mg/hs/"]

    # Extract brand and model from start_urls
    brand_name = 'MG'
    model_name = 'HS'

    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.FaqInfoJsonPipeline': 300,
            'sawari-expert.pipelines.FaqInfoCsvPipeline': 400,
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

        # Extract model name from the URL or page title
        try:
            # Try to extract from h1 or title
            url_parts = self.start_urls[0].rstrip('/').split('/')
            if len(url_parts) >= 2:
                extracted_brand = url_parts[-2].upper()
                extracted_model = url_parts[-1].upper()
            else:
                extracted_brand = self.brand_name
                extracted_model = self.model_name

            # Update spider attributes with extracted data
            self.brand_name = extracted_brand
            self.model_name = extracted_model

            self.logger.info(f"Extracted brand: {extracted_brand}, model: {extracted_model}")
            model_name = f"{extracted_brand} {extracted_model}"
        except Exception as e:
            model_name = f"{self.brand_name} {self.model_name}"
            self.logger.error(f"[ERROR] Could not extract model name: {e}")
            driver.save_screenshot("error_model_name.png")

        # Scroll to FAQ section
        try:
            # Wait for page to load
            time.sleep(3)

            # Find FAQ section - try multiple selectors
            faq_section = None
            faq_xpaths = [
                "//h2[contains(text(), 'FAQs')]",
                "//h2[contains(text(), 'FAQ')]",
                "//div[contains(@class, 'rich-text-class')]//h2",
                "//*[contains(text(), 'FAQs')]"
            ]

            for xpath in faq_xpaths:
                try:
                    faq_section = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    self.logger.info(f"Found FAQ section using xpath: {xpath}")
                    break
                except:
                    continue

            if not faq_section:
                self.logger.warning("Could not find FAQ section heading, searching for accordion elements directly")
                # Try to find accordion elements directly
                try:
                    first_accordion = driver.find_element(By.XPATH, "//div[@data-testid='accordion']")
                    faq_section = first_accordion
                    self.logger.info("Found FAQ section by accordion element")
                except:
                    self.logger.error("Could not find FAQ section at all")
                    driver.save_screenshot("error_faq_not_found.png")
                    return

            # Scroll to FAQ section
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", faq_section)
            time.sleep(2)

            # Take screenshot for debugging
            driver.save_screenshot("faq_section_carexpert.png")

            # Extract FAQ questions and answers
            faq_items = self.extract_faqs(driver, model_name)
            for item in faq_items:
                yield item

        except Exception as e:
            self.logger.error(f"Error processing FAQ section: {e}")
            driver.save_screenshot("error_faq_scroll.png")
            import traceback
            self.logger.error(traceback.format_exc())

    def extract_faqs(self, driver, model_name):
        """Extract FAQ questions and answers from CarExpert accordion elements"""
        faq_items = []

        try:
            # Wait a moment for any animations to complete
            time.sleep(1)

            # Save page source for debugging
            try:
                import os
                os.makedirs("debug_output", exist_ok=True)
                with open(f"debug_output/faq_carexpert_{model_name.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                self.logger.info(f"Saved page source to debug_output/faq_carexpert_{model_name.replace(' ', '_')}.html")
            except Exception as e:
                self.logger.warning(f"Could not save page source: {e}")

            # Find all FAQ accordion elements
            self.logger.info("Looking for FAQ accordion elements with data-testid='accordion'")

            # Scroll down to load all accordions
            self.logger.info("Scrolling to load all FAQ elements...")
            last_height = driver.execute_script("return document.body.scrollHeight")

            # Scroll multiple times to ensure all content is loaded
            for i in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # Scroll back to FAQ section
            try:
                faq_heading = driver.find_element(By.XPATH, "//h2[contains(text(), 'FAQs')]")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});", faq_heading)
                time.sleep(1)
            except:
                pass

            # Find all accordion elements
            accordion_elements = driver.find_elements(
                By.XPATH,
                "//div[@data-testid='accordion']"
            )

            self.logger.info(f"Found {len(accordion_elements)} accordion elements")

            # If no accordions found, try alternative selector
            if len(accordion_elements) == 0:
                self.logger.info("Trying alternative selector for accordions...")
                accordion_elements = driver.find_elements(
                    By.XPATH,
                    "//h3[@data-testid='accordion-header']/.."
                )
                self.logger.info(f"Found {len(accordion_elements)} accordion elements with alternative selector")

            # Process each FAQ accordion
            for idx, accordion_elem in enumerate(accordion_elements):
                try:
                    self.logger.info(f"Processing accordion {idx + 1}/{len(accordion_elements)}")

                    # Scroll accordion into view
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", accordion_elem)
                    time.sleep(0.5)

                    # Find the question button
                    try:
                        question_button = accordion_elem.find_element(
                            By.XPATH,
                            ".//button[@data-testid='accordion-header-button']"
                        )
                    except:
                        # Fallback: find any button in the accordion
                        question_button = accordion_elem.find_element(By.XPATH, ".//button")

                    # Get question text
                    try:
                        question_elem = accordion_elem.find_element(
                            By.XPATH,
                            ".//span[@data-testid='accordion-header-title-text']"
                        )
                        question_text = question_elem.text.strip()
                    except:
                        # Fallback: get text from button
                        question_text = question_button.text.strip()

                    self.logger.info(f"Question: {question_text[:60]}...")

                    # Check if accordion is already expanded
                    is_expanded = question_button.get_attribute("aria-expanded") == "true"

                    # Click to expand if not already expanded
                    if not is_expanded:
                        try:
                            driver.execute_script("arguments[0].click();", question_button)
                            time.sleep(1)  # Wait for expansion animation
                            self.logger.info(f"Clicked to expand accordion {idx + 1}")
                        except Exception as e:
                            self.logger.warning(f"Could not click accordion button: {e}")
                            # Try regular click
                            try:
                                question_button.click()
                                time.sleep(1)
                            except:
                                self.logger.error(f"Failed to expand accordion {idx + 1}")
                                continue
                    else:
                        self.logger.info(f"Accordion {idx + 1} already expanded")

                    # Wait for content to be visible
                    time.sleep(0.5)

                    # Get answer text from the content div
                    answer_text = ""
                    try:
                        # Try to find the content div
                        content_div = accordion_elem.find_element(
                            By.XPATH,
                            ".//div[@data-testid='accordion-content']"
                        )

                        # Get the text content
                        # Try to find paragraph inside content
                        try:
                            answer_elem = content_div.find_element(By.XPATH, ".//p")
                            answer_text = answer_elem.text.strip()
                        except:
                            # Fallback: get all text from content div
                            answer_text = content_div.text.strip()

                        self.logger.info(f"Answer: {answer_text[:60]}...")

                    except Exception as e:
                        self.logger.error(f"Error extracting answer for accordion {idx + 1}: {e}")
                        # Try alternative method - get text from div with specific class
                        try:
                            answer_elem = accordion_elem.find_element(
                                By.XPATH,
                                ".//div[contains(@class, '_1ivmml530d')]//p"
                            )
                            answer_text = answer_elem.text.strip()
                            self.logger.info(f"Answer (alternative method): {answer_text[:60]}...")
                        except:
                            self.logger.error(f"Could not extract answer with any method")
                            continue

                    # Clean up question and answer
                    question_text = question_text.strip()
                    answer_text = answer_text.strip()

                    # Remove any leading "Q:" or "A:" markers if present
                    if question_text.startswith("Q:"):
                        question_text = question_text[2:].strip()
                    if answer_text.startswith("A:"):
                        answer_text = answer_text[2:].strip()

                    # Create FAQ item if both question and answer are present
                    if question_text and answer_text:
                        faq_item = {
                            "modelName": model_name,
                            "faqQuestion": question_text,
                            "faqAnswer": answer_text
                        }
                        faq_items.append(faq_item)
                        self.logger.info(f"✓ Extracted FAQ {idx + 1}: Q={question_text[:40]}... A={answer_text[:40]}...")
                    else:
                        self.logger.warning(f"Skipped FAQ {idx + 1} - empty question or answer")

                    # Optional: collapse the accordion to clean up
                    # (commented out to keep them expanded for potential re-extraction)
                    # if not is_expanded:
                    #     driver.execute_script("arguments[0].click();", question_button)
                    #     time.sleep(0.3)

                except Exception as e:
                    self.logger.error(f"Error processing accordion element {idx + 1}: {e}")
                    import traceback
                    self.logger.error(traceback.format_exc())
                    continue

        except Exception as e:
            self.logger.error(f"[ERROR] Error extracting FAQs: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_faq_extraction_carexpert.png")

        self.logger.info(f"Total FAQs extracted: {len(faq_items)}")
        return faq_items
