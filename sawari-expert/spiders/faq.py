import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time


class FaqSpider(scrapy.Spider):
    name = "faq"
    allowed_domains = ["cardekho.com"]
    start_urls = ["https://www.cardekho.com/mahindra/xuv700"]

    # Extract brand and model from start_urls

    brand_name = 'Mahindra'
    model_name = 'xuv700'
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

        # Extract model name from h1
        try:
            model_name_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'thcHeading')]"))
            )
            full_name = model_name_elem.text.strip()

            # Extract model name
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

        # Scroll to FAQ section
        try:
            # First try to find the FAQ heading with model name
            faq_heading = None
            try:
                faq_heading = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//h2[contains(text(), '{model_name} Questions')]"))
                )
                self.logger.info(f"Found FAQ heading with model name: '{model_name} Questions'")
            except:
                # Fallback: Look for generic "Questions" heading
                try:
                    faq_heading = driver.find_element(By.XPATH, "//h2[contains(text(), 'Questions')]")
                    self.logger.info("Found FAQ heading: 'Questions & answers' or similar")
                except:
                    # Second fallback: Look for section with faqTabbin class
                    try:
                        faq_heading = driver.find_element(By.XPATH, "//section[contains(@class, 'faqTabbin')]//h2")
                        self.logger.info(f"Found FAQ heading in faqTabbin section: {faq_heading.text}")
                    except:
                        self.logger.warning("Could not find FAQ heading, will attempt to find FAQ elements directly")

            # Scroll to FAQ section if heading found
            if faq_heading:
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", faq_heading)
                time.sleep(2)

            # Take screenshot for debugging
            driver.save_screenshot("faq_section.png")

            # Extract FAQ questions and answers
            faq_items = self.extract_faqs(driver, model_name)
            for item in faq_items:
                yield item

        except Exception as e:
            self.logger.error(f"Error scrolling to FAQ section: {e}")
            driver.save_screenshot("error_faq_scroll.png")

    def extract_faqs(self, driver, model_name):
        """Extract FAQ questions and answers"""
        faq_items = []

        try:
            # Wait for FAQ section to be present
            time.sleep(1)

            # Save page source for debugging
            try:
                import os
                os.makedirs("debug_output", exist_ok=True)
                with open(f"debug_output/faq_page_source_{model_name.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                self.logger.info(f"Saved page source to debug_output/faq_page_source_{model_name.replace(' ', '_')}.html")
            except Exception as e:
                self.logger.warning(f"Could not save page source: {e}")

            # Find all FAQ accordion elements in the first tab (common FAQs)
            # First check if tabs are present
            self.logger.info("Looking for FAQ elements using data-track-section='FAQs'")
            faq_elements = driver.find_elements(
                By.XPATH,
                "//div[@data-track-section='FAQs']//div[contains(@class, 'toggleAccordion')]"
            )

            # Fallback: try without data-track-section if not found
            if len(faq_elements) == 0:
                self.logger.info("No elements found with data-track-section, trying gsc-ta-active class")
                faq_elements = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'gsc-ta-active')]//div[contains(@class, 'toggleAccordion')]"
                )

            # Second fallback: try finding any accordion in faqTabbin section
            if len(faq_elements) == 0:
                self.logger.info("Trying to find FAQs in faqTabbin section")
                faq_elements = driver.find_elements(
                    By.XPATH,
                    "//section[contains(@class, 'faqTabbin')]//div[contains(@class, 'toggleAccordion')]"
                )

            self.logger.info(f"Found {len(faq_elements)} FAQ elements in first tab")

            # If still no elements, log available structure
            if len(faq_elements) == 0:
                self.logger.warning("No FAQ elements found! Checking page structure...")
                try:
                    sections = driver.find_elements(By.XPATH, "//section")
                    self.logger.info(f"Found {len(sections)} section elements")
                    for idx, section in enumerate(sections[:5]):
                        class_attr = section.get_attribute("class")
                        self.logger.info(f"Section {idx}: class='{class_attr}'")
                except Exception as e:
                    self.logger.error(f"Error checking page structure: {e}")

            # Process each FAQ element
            for faq_elem in faq_elements:
                try:
                    # Extract question text
                    question_elem = faq_elem.find_element(By.XPATH, ".//span[contains(@class, 'accordianheader')]")
                    question_text = question_elem.text.strip()

                    self.logger.debug(f"Raw question text: {question_text[:50]}...")

                    # Clean up the question text (remove the "Q ) " prefix and any trailing icons)
                    if question_text.startswith("Q )"):
                        question_text = question_text[3:].strip()

                    # Remove any icon class text at the end
                    if question_text.endswith("icon-addition") or question_text.endswith("icon-minus"):
                        question_text = question_text.rsplit(" ", 1)[0].strip()

                    # Extract answer text (need to click to expand first)
                    try:
                        # Click to expand
                        driver.execute_script("arguments[0].click();", question_elem)
                        time.sleep(0.5)  # Brief pause for animation

                        # Get answer text
                        answer_elem = faq_elem.find_element(By.XPATH, ".//div[contains(@class, 'content')]")
                        answer_text = answer_elem.text.strip()

                        self.logger.debug(f"Raw answer text: {answer_text[:50]}...")

                        # Clean up the answer text (remove the "A ) " prefix if present)
                        if answer_text.startswith("A )"):
                            answer_text = answer_text[3:].strip()

                        # If answer is empty after cleanup, try alternative extraction
                        if not answer_text:
                            try:
                                answer_elem = faq_elem.find_element(By.XPATH, ".//div[@data-gsp-accordion-content]")
                                answer_text = answer_elem.text.strip()
                                if answer_text.startswith("A )"):
                                    answer_text = answer_text[3:].strip()
                                self.logger.debug(f"Used alternative answer extraction: {answer_text[:50]}...")
                            except:
                                pass

                        # Create and add the FAQ item
                        if question_text and answer_text:
                            faq_item = {
                                "modelName": model_name,
                                "faqQuestion": question_text,
                                "faqAnswer": answer_text
                            }
                            faq_items.append(faq_item)
                            self.logger.info(f"✓ Extracted FAQ: Q={question_text[:40]}... A={answer_text[:40]}...")
                        else:
                            self.logger.warning(f"Skipped FAQ with empty question or answer: Q='{question_text}' A='{answer_text}'")

                    except Exception as e:
                        self.logger.error(f"Error extracting answer for question '{question_text}': {e}")
                        import traceback
                        self.logger.debug(traceback.format_exc())

                except Exception as e:
                    self.logger.error(f"Error processing FAQ element: {e}")

            # Now check the second tab for user questions
            try:
                # Find and click the "Latest Questions" tab
                questions_tab = None
                try:
                    # Try by title attribute first
                    questions_tab = driver.find_element(By.XPATH, "//li[@title='Latest Questions']")
                except:
                    # Fallback: try by text content
                    try:
                        questions_tab = driver.find_element(By.XPATH, "//li[contains(text(), 'Latest Questions')]")
                    except:
                        # Second fallback: try selecting second li in the tab list
                        try:
                            questions_tab = driver.find_element(By.XPATH, "//ul[@class='gsc-ta-clickWrap']//li[2]")
                        except:
                            self.logger.warning("Could not find 'Latest Questions' tab")

                if questions_tab:
                    self.logger.info(f"Found 'Latest Questions' tab, clicking it...")
                    driver.execute_script("arguments[0].click();", questions_tab)
                    time.sleep(2)  # Wait for tab content to load

                    # Find all user question accordion elements
                    user_faq_elements = driver.find_elements(
                        By.XPATH,
                        "//div[@data-track-section='Latest Questions']//div[contains(@class, 'toggleAccordion')]"
                    )

                    self.logger.info(f"Found {len(user_faq_elements)} user question elements")

                    # Process each user FAQ element
                    for faq_elem in user_faq_elements:
                        try:
                            # Extract question text
                            question_elem = faq_elem.find_element(By.XPATH, ".//span[contains(@class, 'accordianheader')]")
                            question_text = question_elem.text.strip()

                            # Clean up the question text
                            if question_text.startswith("Q )"):
                                question_text = question_text[3:].strip()

                            # Extract answer text (need to click to expand first)
                            try:
                                # Click to expand
                                driver.execute_script("arguments[0].click();", question_elem)
                                time.sleep(0.5)  # Brief pause for animation

                                # Get answer text - different structure for user questions
                                answer_elem = faq_elem.find_element(By.XPATH, ".//div[contains(@class, 'ans')]")
                                answer_text = answer_elem.text.strip()

                                # Clean up the answer text
                                if answer_text.startswith("A )"):
                                    answer_text = answer_text[3:].strip()

                                # Remove "Read More" text if present
                                read_more_idx = answer_text.rfind("Read More")
                                if read_more_idx > 0:
                                    answer_text = answer_text[:read_more_idx].strip()

                                # Create and add the FAQ item
                                if question_text and answer_text:
                                    faq_item = {
                                        "modelName": model_name,
                                        "faqQuestion": question_text,
                                        "faqAnswer": answer_text
                                    }
                                    faq_items.append(faq_item)
                                    self.logger.info(f"✓ Extracted user FAQ: Q={question_text[:40]}... A={answer_text[:40]}...")
                                else:
                                    self.logger.warning(f"Skipped user FAQ with empty question or answer")

                            except Exception as e:
                                self.logger.error(f"Error extracting answer for user question '{question_text}': {e}")
                                import traceback
                                self.logger.debug(traceback.format_exc())

                        except Exception as e:
                            self.logger.error(f"Error processing user FAQ element: {e}")
                            import traceback
                            self.logger.debug(traceback.format_exc())
                else:
                    self.logger.warning("Skipping user questions tab - tab not found")

            except Exception as e:
                self.logger.error(f"Error accessing user questions tab: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())

        except Exception as e:
            self.logger.error(f"[ERROR] Error finding FAQ elements: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            driver.save_screenshot("error_faq_extraction.png")

        self.logger.info(f"Total FAQs extracted: {len(faq_items)}")
        return faq_items
