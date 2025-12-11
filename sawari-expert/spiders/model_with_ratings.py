import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from ..items import ModelInfoItem, RatingInfoItem


class ModelWithRatingsSpider(scrapy.Spider):
    name = "model-rating"
    allowed_domains = ["autocarindia.com"]
    start_urls = ["https://www.autocarindia.com/cars/mahindra/xuv700"]

    # Extract brand and model from start_urls


    brand_name = 'Mahendra'
    model_name = 'xuv700'
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.ModelInfoJsonPipeline': 300,
            'sawari-expert.pipelines.ModelInfoCsvPipeline': 400,
            'sawari-expert.pipelines.RatingInfoJsonPipeline': 500,
            'sawari-expert.pipelines.RatingInfoCsvPipeline': 600,
        },
        'DUPEFILTER_CLASS': 'scrapy.dupefilters.RFPDupeFilter',
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

        # Extract model info
        model_info = self.extract_model_info(driver)

        # Update brand_name and model_name from extracted data
        self.brand_name = model_info.get("brandName", self.brand_name)
        self.model_name = model_info.get("modelName", self.model_name)

        # Yield model info to the pipelines
        yield model_info

        # Extract rating info
        rating_items = self.extract_ratings(driver, model_info["modelName"])

        # Save rating items to a debug file
        try:
            import json
            import os

            # Create debug directory if it doesn't exist
            debug_dir = "debug_output"
            os.makedirs(debug_dir, exist_ok=True)

            # Save the ratings data to a JSON file
            debug_filename = f"{debug_dir}/ratings_debug_{model_info['modelName'].replace(' ', '_')}.json"
            with open(debug_filename, 'w', encoding='utf-8') as f:
                json.dump([dict(item) for item in rating_items], f, indent=4)

            self.logger.info(f"[DEBUG] Saved ratings data to {debug_filename}")
        except Exception as e:
            self.logger.error(f"[ERROR] Failed to save debug file: {e}")

        # Yield each rating item
        for item in rating_items:
            yield item

    def extract_model_info(self, driver):
        """Extract model information"""
        # Extract brand and model name
        try:
            car_name_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'text-display-sm')]"))
            )
            car_name_full = car_name_elem.text.strip()
            parts = car_name_full.split()
            brand_name = parts[0] if len(parts) > 0 else ""
            model_name = " ".join(parts[1:]) if len(parts) > 1 else ""
            self.logger.info(f"Found car: {brand_name} {model_name}")
        except Exception as e:
            brand_name = model_name = ""
            self.logger.error(f"[ERROR] Could not extract car name info: {e}")

        # Extract model description
        try:
            # Scroll down to find description section
            description_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'styledInnerHTML_styledHtml')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", description_elem)
            time.sleep(1)

            # Check if "Show more" button exists and click it
            try:
                show_more_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'text-primary-red-100') and contains(text(), 'Show more')]"))
                )
                self.logger.info("Found 'Show more' button, clicking it...")
                driver.execute_script("arguments[0].click();", show_more_button)
                time.sleep(2)  # Wait for expanded content to load
            except Exception as button_e:
                self.logger.info("No 'Show more' button found or couldn't click it: %s", button_e)

            # Extract only the first paragraph
            try:
                # Get only the first paragraph element
                first_paragraph = description_elem.find_element(By.XPATH, ".//p[1]")
                model_description = first_paragraph.text.strip()
                self.logger.info(f"Found description (first paragraph): {model_description[:100]}...")
            except Exception as p_e:
                self.logger.error(f"Error extracting first paragraph: {p_e}")
                # Fallback: try to get just the text before any headings or subheadings
                try:
                    full_text = description_elem.text.strip()
                    lines = full_text.split('\n')
                    if len(lines) > 1:
                        if len(lines[1].strip()) < 30:
                            model_description = lines[0]
                        else:
                            model_description = lines[0]
                    else:
                        model_description = full_text
                    self.logger.info(f"Used fallback method for description: {model_description[:100]}...")
                except Exception as fallback_e:
                    model_description = ""
                    self.logger.error(f"Fallback also failed: {fallback_e}")

        except Exception as e:
            model_description = ""
            self.logger.error(f"[ERROR] Could not extract model description: {e}")
            driver.save_screenshot("description_error.png")

        # Extract body type
        try:
            body_style_elem = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'flex items-center justify-between py-2 border-border border-b text-sm')][.//div[contains(., 'Body Style')]]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", body_style_elem)
            body_type = body_style_elem.find_element(By.XPATH, ".//div[contains(@class, 'text-button-sm')]").text.strip()
            self.logger.info(f"Found body type: {body_type}")
        except Exception as e:
            body_type = ""
            self.logger.error(f"[ERROR] Could not extract body type: {e}")

        # Return model info as ModelInfoItem
        return ModelInfoItem(
            brandName=brand_name,
            modelName=model_name,
            modelDescription=model_description,
            modelTagline=" ",
            modelIsHiglighted=" ",
            bodyType=body_type,
        )

    def extract_ratings(self, driver, model_name):
        """Extract ratings from DOM elements - Expert Review section"""
        rating_items = []

        try:
            self.logger.info("=" * 60)
            self.logger.info("Starting DOM-based rating extraction...")
            self.logger.info("=" * 60)

            # Scroll down to load the expert review section
            self.logger.info("Scrolling to Expert Review section...")
            for i in range(5):
                scroll_position = 0.4 + (i * 0.15)
                driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position});")
                time.sleep(1.5)

            # Wait for the expert review section to load
            try:
                expert_review_heading = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h2[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'expert review')]"))
                )
                self.logger.info(f"✓ Found Expert Review heading: {expert_review_heading.text}")

                # Scroll to the expert review section
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", expert_review_heading)
                time.sleep(2)

                # Take screenshot for debugging
                import os
                os.makedirs("debug_output", exist_ok=True)
                driver.save_screenshot(f"debug_output/expert_review_section_{model_name.replace(' ', '_')}.png")

            except Exception as e:
                self.logger.error(f"Could not find 'Expert Review' heading: {e}")
                driver.save_screenshot(f"debug_output/no_expert_review_{model_name.replace(' ', '_')}.png")
                return rating_items

            # METHOD: Extract ratings from accordion layout structure
            self.logger.info("Extracting ratings from accordion layout...")

            try:
                # Wait a bit for the accordion to render
                time.sleep(3)

                # Save page source for debugging
                try:
                    import os
                    os.makedirs("debug_output", exist_ok=True)
                    with open(f"debug_output/page_source_{model_name.replace(' ', '_')}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    self.logger.info(f"✓ Saved page source for debugging")
                except Exception as e:
                    self.logger.warning(f"Could not save page source: {e}")

                # First try: Extract from accordion layout (new structure)
                self.logger.info("Attempting to find accordion items with data-slot='accordion-item'")
                accordion_items = driver.find_elements(By.XPATH, "//div[@data-slot='accordion-item']")
                self.logger.info(f"Found {len(accordion_items)} accordion items (new structure)")

                # If no accordion items, also check for any elements with accordion pattern
                if len(accordion_items) == 0:
                    self.logger.info("No accordion items found, checking for accordion-related divs...")
                    accordion_divs = driver.find_elements(By.XPATH, "//div[@data-slot='accordion']")
                    self.logger.info(f"Found {len(accordion_divs)} accordion divs")

                # Track seen categories to avoid duplicates
                seen_categories = set()

                if len(accordion_items) > 0:
                    # New accordion-based structure
                    self.logger.info("Using accordion-based extraction method")
                    for idx, accordion_item in enumerate(accordion_items):
                        try:
                            # Get category name from the span inside the button
                            category_name = None
                            try:
                                category_elem = accordion_item.find_element(By.XPATH,
                                    ".//button[@data-slot='accordion-trigger']//span[contains(@class, 'text-primary-black') and contains(@class, 'font-medium')]")
                                category_name = category_elem.text.strip()
                                self.logger.debug(f"Accordion {idx}: Found category element with text: '{category_name}'")
                            except Exception as cat_e:
                                self.logger.debug(f"Accordion {idx}: Could not extract category name: {cat_e}")

                            self.logger.info(f"Accordion {idx}: category_name = '{category_name}'")

                            # Skip if empty, too short, or already seen
                            if not category_name or len(category_name) < 5 or category_name in seen_categories:
                                self.logger.debug(f"Skipping accordion {idx}: empty/short/duplicate")
                                continue

                            seen_categories.add(category_name)

                            # Get rating - look for the next sibling div with absolute positioning that contains font-semibold
                            rating_value = None
                            try:
                                # The rating div is a sibling of the accordion div, both inside a relative div
                                # Find the parent of the accordion (should be a div with relative class)
                                self.logger.debug(f"Accordion {idx}: Looking for parent relative container...")
                                parent_container = accordion_item.find_element(By.XPATH,
                                    "./ancestor::div[contains(@class, 'relative')][1]")
                                self.logger.debug(f"Accordion {idx}: Found parent container, looking for rating element...")
                                rating_elem = parent_container.find_element(By.XPATH,
                                    ".//div[contains(@class, 'absolute') and contains(@class, 'top-2')]//p[@class='font-semibold']")
                                rating_value = rating_elem.text.strip()
                                self.logger.debug(f"Accordion {idx}: Successfully extracted rating via method 1")
                            except Exception as rating_e1:
                                self.logger.debug(f"Accordion {idx}: Method 1 failed ({rating_e1}), trying fallback...")
                                # Fallback: try to find by accordion parent relationship
                                try:
                                    accordion_parent = accordion_item.find_element(By.XPATH, "./parent::div[@data-slot='accordion']")
                                    grand_parent = accordion_parent.find_element(By.XPATH, "./parent::div[contains(@class, 'relative')]")
                                    rating_elem = grand_parent.find_element(By.XPATH,
                                        ".//div[contains(@class, 'absolute')]//p[@class='font-semibold']")
                                    rating_value = rating_elem.text.strip()
                                    self.logger.debug(f"Accordion {idx}: Successfully extracted rating via fallback method")
                                except Exception as rating_e2:
                                    self.logger.debug(f"Accordion {idx}: Fallback also failed: {rating_e2}")
                                    pass

                            self.logger.info(f"Accordion {idx}: rating_value = '{rating_value}'")

                            if not rating_value:
                                self.logger.warning(f"Could not find rating for {category_name}")
                                continue

                            # Convert decimal ratings to integers (e.g., "8.0" -> "8")
                            if '.' in rating_value:
                                try:
                                    rating_value = str(int(float(rating_value)))
                                except ValueError:
                                    pass

                            # Validate rating is numeric
                            if rating_value.isdigit():
                                rating_items.append(RatingInfoItem(
                                    modelName=model_name,
                                    ratingCategoryName=category_name,
                                    rating=rating_value
                                ))
                                self.logger.info(f"✓ Extracted (accordion): {category_name} = {rating_value}")
                            else:
                                self.logger.warning(f"Invalid rating value: '{rating_value}' for {category_name}")

                        except Exception as e:
                            self.logger.warning(f"Error processing accordion {idx}: {e}")
                            import traceback
                            self.logger.debug(traceback.format_exc())
                            continue
                else:
                    # Fallback to old grid layout structure
                    self.logger.info("No accordion items found, trying grid layout...")
                    rating_cards = driver.find_elements(By.XPATH,
                        "//div[contains(@class, 'grid') and contains(@class, 'rounded-lg') and contains(@class, 'border')]")

                    self.logger.info(f"Found {len(rating_cards)} rating cards in grid layout")

                    for idx, card in enumerate(rating_cards):
                        try:
                            # Get category name - look for text-primary-black with font-medium
                            category_name = None
                            try:
                                category_elem = card.find_element(By.XPATH,
                                    ".//p[contains(@class, 'text-primary-black') and contains(@class, 'font-medium')]")
                                category_name = category_elem.text.strip()
                            except Exception:
                                pass

                            self.logger.debug(f"Card {idx}: category_name = '{category_name}'")

                            # Skip if empty, too short, or already seen
                            if not category_name or len(category_name) < 5 or category_name in seen_categories:
                                self.logger.debug(f"Skipping card {idx}: empty/short/duplicate")
                                continue

                            seen_categories.add(category_name)

                            # Get rating - look for font-semibold p tag
                            rating_value = None
                            try:
                                rating_elem = card.find_element(By.XPATH, ".//p[@class='font-semibold']")
                                rating_value = rating_elem.text.strip()
                            except Exception:
                                pass

                            self.logger.debug(f"Card {idx}: rating_value = '{rating_value}'")

                            if not rating_value:
                                self.logger.warning(f"Could not find rating for {category_name}")
                                continue

                            # Convert decimal ratings to integers (e.g., "8.0" -> "8")
                            if '.' in rating_value:
                                try:
                                    rating_value = str(int(float(rating_value)))
                                except ValueError:
                                    pass

                            # Validate rating is numeric
                            if rating_value.isdigit():
                                rating_items.append(RatingInfoItem(
                                    modelName=model_name,
                                    ratingCategoryName=category_name,
                                    rating=rating_value
                                ))
                                self.logger.info(f"✓ Extracted: {category_name} = {rating_value}")
                            else:
                                self.logger.warning(f"Invalid rating value: '{rating_value}' for {category_name}")

                        except Exception as e:
                            self.logger.debug(f"Skipping card {idx}: {e}")
                            continue

                # Validate we got 7 ratings (standard for this site)
                if len(rating_items) == 7:
                    self.logger.info("✓✓✓ Successfully extracted all 7 ratings!")
                elif len(rating_items) > 0:
                    self.logger.warning(f"⚠ Extracted {len(rating_items)} ratings (expected 7)")
                    # Log which categories were found
                    found_categories = [item['ratingCategoryName'] for item in rating_items]
                    self.logger.info(f"Found categories: {found_categories}")
                else:
                    self.logger.error("✗ Failed to extract any ratings from primary method")

                    # Fallback: Try alternative selector
                    self.logger.info("Trying alternative selector method...")
                    rating_items = self._extract_ratings_alternative(driver, model_name)

            except Exception as e:
                self.logger.error(f"Error finding accordion/grid elements: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

                # Try alternative method
                rating_items = self._extract_ratings_alternative(driver, model_name)

        except Exception as e:
            self.logger.error(f"[ERROR] Critical error in extract_ratings: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        self.logger.info(f"=" * 60)
        self.logger.info(f"Rating extraction complete: {len(rating_items)} ratings found")
        self.logger.info(f"=" * 60)

        return rating_items

    def _extract_ratings_alternative(self, driver, model_name):
        """Alternative method: Extract ratings using known category names"""
        rating_items = []

        try:
            self.logger.info("ALTERNATIVE METHOD: Using known category names...")

            # Try finding all rating sections by looking for the category text patterns
            rating_categories = [
                "Exterior Design And Engineering",
                "Interior Space And Comfort",
                "Performance And Refinement",
                "Mileage / Range And Efficiency",
                "Ride Comfort And Handling",
                "Features And Safety",
                "Value For Money"
            ]

            for category in rating_categories:
                try:
                    # Find the paragraph with this category text
                    category_elem = None
                    rating_value = None

                    # Method 1: Look for accordion structure with span containing category
                    try:
                        category_elem = driver.find_element(By.XPATH,
                            f"//span[contains(@class, 'text-primary-black') and contains(@class, 'font-medium') and contains(text(), '{category}')]")
                    except Exception:
                        # Method 2: Look for p tag with text-primary-black containing category (old structure)
                        try:
                            category_elem = driver.find_element(By.XPATH,
                                f"//p[contains(@class, 'text-primary-black') and contains(@class, 'font-medium') and contains(text(), '{category}')]")
                        except Exception:
                            pass

                    # Method 3: Try any p tag with the text
                    if not category_elem:
                        try:
                            category_elem = driver.find_element(By.XPATH,
                                f"//p[contains(@class, 'font-medium') and contains(text(), '{category}')]")
                        except Exception:
                            pass

                    if not category_elem:
                        self.logger.debug(f"Could not find element for {category}")
                        continue

                    # For accordion structure, look for nearby absolute positioned div with rating
                    rating_value = None
                    try:
                        # Try accordion structure first - find the relative parent container
                        accordion_item = category_elem.find_element(By.XPATH,
                            "./ancestor::div[@data-slot='accordion-item']")
                        accordion_parent = accordion_item.find_element(By.XPATH, "./parent::div[@data-slot='accordion']")
                        relative_container = accordion_parent.find_element(By.XPATH, "./parent::div[contains(@class, 'relative')]")
                        # Rating is in absolute positioned div within the same relative container
                        rating_elem = relative_container.find_element(By.XPATH,
                            ".//div[contains(@class, 'absolute') and contains(@class, 'top-2')]//p[@class='font-semibold']")
                        rating_value = rating_elem.text.strip()
                    except Exception:
                        # Fallback to old grid structure
                        try:
                            parent = category_elem.find_element(By.XPATH,
                                "./ancestor::div[contains(@class, 'grid') and contains(@class, 'rounded-lg')]")
                            rating_elem = parent.find_element(By.XPATH, ".//p[@class='font-semibold']")
                            rating_value = rating_elem.text.strip()
                        except Exception:
                            try:
                                parent = category_elem.find_element(By.XPATH,
                                    "./ancestor::div[contains(@class, 'rounded-lg')]")
                                rating_elem = parent.find_element(By.XPATH, ".//p[@class='font-semibold']")
                                rating_value = rating_elem.text.strip()
                            except Exception:
                                self.logger.debug(f"Could not find rating for {category}")

                    if not rating_value:
                        self.logger.debug(f"Could not find rating for {category}")
                        continue

                    # Convert decimal ratings to integers
                    if '.' in rating_value:
                        try:
                            rating_value = str(int(float(rating_value)))
                        except ValueError:
                            pass

                    if rating_value.isdigit():
                        rating_items.append(RatingInfoItem(
                            modelName=model_name,
                            ratingCategoryName=category,
                            rating=rating_value
                        ))
                        self.logger.info(f"✓ Extracted (alt): {category} = {rating_value}")

                except Exception as e:
                    self.logger.debug(f"Error with {category}: {e}")
                    continue

            if len(rating_items) > 0:
                self.logger.info(f"✓ Alternative method extracted {len(rating_items)} ratings")
            else:
                # Final fallback: Try to get all ratings by looking for circular rating displays
                self.logger.info("Trying final fallback method...")
                rating_items = self._extract_ratings_final_fallback(driver, model_name)

        except Exception as e:
            self.logger.error(f"Alternative method also failed: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

        return rating_items

    def _extract_ratings_final_fallback(self, driver, model_name):
        """Final fallback: Look for any p tags with font-semibold and nearby category text"""
        rating_items = []

        try:
            self.logger.info("FINAL FALLBACK: Looking for font-semibold rating elements...")

            # Look for all p elements with font-semibold that contain numbers
            rating_elements = driver.find_elements(By.XPATH, "//p[@class='font-semibold']")
            self.logger.info(f"Found {len(rating_elements)} font-semibold elements")

            seen_categories = set()

            for elem in rating_elements:
                try:
                    rating_value = elem.text.strip()

                    # Check if this looks like a rating (numeric, 1-3 chars)
                    if not rating_value or not rating_value.replace('.', '').isdigit() or len(rating_value) > 4:
                        continue

                    # Try to find parent accordion item first, then fall back to grid
                    parent_card = None
                    category_name = None

                    try:
                        # Try accordion structure - find the relative container
                        relative_container = elem.find_element(By.XPATH,
                            "./ancestor::div[contains(@class, 'relative')][1]")
                        # Look for category in the accordion item within the same relative container
                        category_elem = relative_container.find_element(By.XPATH,
                            ".//div[@data-slot='accordion-item']//span[contains(@class, 'text-primary-black') and contains(@class, 'font-medium')]")
                        category_name = category_elem.text.strip()
                    except Exception:
                        # Fall back to grid structure
                        try:
                            parent_card = elem.find_element(By.XPATH,
                                "./ancestor::div[contains(@class, 'grid') and contains(@class, 'rounded-lg')]")
                            category_elem = parent_card.find_element(By.XPATH,
                                ".//p[contains(@class, 'text-primary-black') and contains(@class, 'font-medium')]")
                            category_name = category_elem.text.strip()
                        except Exception:
                            pass

                    if not category_name:
                        continue

                    if not category_name or len(category_name) < 5 or category_name in seen_categories:
                        continue

                    seen_categories.add(category_name)

                    # Convert decimal ratings to integers
                    if '.' in rating_value:
                        try:
                            rating_value = str(int(float(rating_value)))
                        except (ValueError, TypeError):
                            pass

                    if rating_value.isdigit():
                        rating_items.append(RatingInfoItem(
                            modelName=model_name,
                            ratingCategoryName=category_name,
                            rating=rating_value
                        ))
                        self.logger.info(f"✓ Extracted (fallback): {category_name} = {rating_value}")

                except Exception as e:
                    self.logger.debug(f"Error in fallback extraction: {e}")
                    continue

            self.logger.info(f"Final fallback found {len(rating_items)} ratings")

        except Exception as e:
            self.logger.error(f"Final fallback failed: {e}")

        return rating_items
