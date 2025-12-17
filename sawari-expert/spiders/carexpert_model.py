import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re
import logging

# Suppress verbose Selenium and urllib3 logs
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)


class CarExpertModelSpider(scrapy.Spider):
    name = "carexpert_model"
    allowed_domains = ["carexpert.com.au"]
    start_urls = ["https://www.carexpert.com.au/mg/mg4"]
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.CarExpertModelInfoJsonPipeline': 300,
            'sawari-expert.pipelines.CarExpertModelInfoCsvPipeline': 301,
            'sawari-expert.pipelines.CarExpertFAQJsonPipeline': 302,
            'sawari-expert.pipelines.CarExpertFAQCsvPipeline': 303,
            'sawari-expert.pipelines.CarExpertProsConsJsonPipeline': 304,
            'sawari-expert.pipelines.CarExpertProsConsCsvPipeline': 305,
        }
    }

    def start_requests(self):
        for url in self.start_urls:
            yield SeleniumRequest(
                url=url,
                callback=self.parse_model,
                wait_time=20,
                dont_filter=True,
                meta={'dont_cache': True}
            )

    def parse_model(self, response):
        driver = response.meta.get("driver")
        
        if not driver:
            self.logger.error("[ERROR] WebDriver not found")
            return

        # Extract model name from h1
        try:
            model_name_elem = driver.find_element(By.XPATH, "//h1[contains(@class, '_1ivmml5i')]")
            model_name = model_name_elem.text.strip()
            self.logger.info(f"[INFO] Model name: {model_name}")
        except Exception as e:
            model_name = ""
            self.logger.error(f"[ERROR] Could not extract model name: {e}")

        # Click Read More button to expand description
        try:
            read_more_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Read More')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", read_more_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", read_more_btn)
            self.logger.info("[INFO] Clicked 'Read More' button")
            time.sleep(2)
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not click 'Read More' button: {e}")

        # Extract model description
        try:
            description_container = driver.find_element(By.XPATH, "//div[contains(@class, '_19m0jur22')]")
            description_paragraphs = description_container.find_elements(By.TAG_NAME, "p")
            model_description = " ".join([p.text.strip() for p in description_paragraphs])
            self.logger.info(f"[INFO] Model description extracted: {len(model_description)} chars")
        except Exception as e:
            model_description = ""
            self.logger.error(f"[ERROR] Could not extract model description: {e}")

        # Click Show Stats button
        try:
            show_stats_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Show Stats')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", show_stats_btn)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", show_stats_btn)
            self.logger.info("[INFO] Clicked 'Show Stats' button")
            time.sleep(2)
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not click 'Show Stats' button: {e}")

        # Extract body type
        body_type = ""
        try:
            stats_container = driver.find_element(By.XPATH, "//div[contains(@class, '_19m0jurx')]")
            body_type_elem = stats_container.find_element(By.XPATH, ".//p[text()='Body Types']/following-sibling::p")
            body_type = body_type_elem.text.strip()
            self.logger.info(f"[INFO] Body type: {body_type}")
        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract body type: {e}")

        # Extract brand name and model name from the full model name
        # Assuming format like "Mahindra Scorpio" or "Maruti Suzuki Swift"
        brand_name = ""
        actual_model_name = model_name
        
        if model_name:
            parts = model_name.split(maxsplit=1)
            if len(parts) >= 2:
                brand_name = parts[0]
                actual_model_name = parts[1]
            elif len(parts) == 1:
                # If only one word, use it as model name
                actual_model_name = parts[0]
        
        self.logger.info(f"[INFO] Brand: {brand_name}, Model: {actual_model_name}")

        # Yield model information with all required fields
        yield {
            "brandName": brand_name,
            "modelName": actual_model_name,
            "modelDescription": model_description,
            "modelTagline": "",
            "modelIsHighlighted": "",
            "bodyType": body_type
        }

        # Extract Pros and Cons
        self.logger.info("[INFO] ========== STARTING PROS/CONS EXTRACTION ==========")
        try:
            # Create debug file for pros/cons
            import os
            debug_dir = "debug_output"
            os.makedirs(debug_dir, exist_ok=True)
            safe_model_name = actual_model_name.replace(' ', '_').replace('/', '_')
            pros_cons_debug_file = os.path.join(debug_dir, f"pros_cons_{safe_model_name}.html")
            
            # Save the entire page source for debugging
            page_source_file = os.path.join(debug_dir, f"full_page_{safe_model_name}.html")
            with open(page_source_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            self.logger.info(f"[DEBUG] Saved full page source to {page_source_file}")
            
            self.logger.info("[INFO] Scrolling down to load pros/cons section...")
            
            # Scroll down the page incrementally to ensure content loads
            for i in range(3):
                scroll_position = (i + 1) * (driver.execute_script("return document.body.scrollHeight") / 4)
                driver.execute_script(f"window.scrollTo(0, {scroll_position});")
                time.sleep(1.5)
                self.logger.info(f"[DEBUG] Scrolled to position {i+1}/3")
            
            self.logger.info("[INFO] Looking for pros/cons section...")
            
            # Check if pros/cons section exists on this page
            pros_cons_section = None
            try:
                # Using the actual class from the HTML you provided
                pros_cons_section = driver.find_element(By.XPATH, "//div[contains(@class, '_35h4t0m')]")
                self.logger.info("[INFO] ✓ Pros/cons section found!")
            except Exception as e:
                self.logger.warning(f"[WARNING] Pros/cons section NOT found with _35h4t0m class")
                
                # Try to find h3 with "Pros" text (might exist without the container class)
                try:
                    pros_h3 = driver.find_element(By.XPATH, "//h3[contains(@class, '_1ivmml5') and contains(text(), 'Pros')]")
                    # Get the grandparent container
                    pros_cons_section = pros_h3.find_element(By.XPATH, "ancestor::div[contains(@class, '_35h4t0m') or contains(@class, '_1ivmml53pt')][1]")
                    self.logger.info("[INFO] ✓ Found pros/cons via h3 ancestor")
                except Exception as e2:
                    self.logger.warning(f"[WARNING] Could not find pros/cons via h3: {e2}")
                    
                    # Last attempt: check if page even has pros/cons
                    try:
                        # Just check if "Pros" h3 exists anywhere
                        if driver.find_elements(By.XPATH, "//h3[contains(text(), 'Pros')]"):
                            self.logger.warning("[WARNING] 'Pros' h3 exists but parent container not found")
                        else:
                            self.logger.info("[INFO] This page does not have a pros/cons section - skipping")
                            raise Exception("No pros/cons section on this page")
                    except:
                        pass
            
            # If we found the section, extract pros and cons
            if pros_cons_section:
                # Scroll to pros/cons section
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pros_cons_section)
                time.sleep(1)
                self.logger.info("[INFO] Scrolled to pros/cons section")
                
                # Save the entire pros/cons section HTML for debugging
                section_html = pros_cons_section.get_attribute('outerHTML')
                with open(pros_cons_debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- Model: {actual_model_name} -->\n")
                    f.write(f"<!-- URL: {response.url} -->\n")
                    f.write(f"<!-- Section class: _35h4t0m -->\n\n")
                    f.write(section_html)
                self.logger.info(f"[DEBUG] Saved pros/cons HTML to {pros_cons_debug_file}")
                
                # Extract Pros using the actual HTML structure
                pros = []
                try:
                    self.logger.info("[DEBUG] Attempting to find Pros...")
                    
                    # Find h3 with "Pros" text
                    pros_h3 = pros_cons_section.find_element(By.XPATH, ".//h3[contains(text(), 'Pros')]")
                    # Get the parent div that contains both h3 and ul
                    pros_container = pros_h3.find_element(By.XPATH, "ancestor::div[contains(@class, '_1ivmml5yu')][1]")
                    # Get the ul
                    pros_ul = pros_container.find_element(By.XPATH, ".//ul[contains(@class, '_6h1tsc2')]")
                    pros_items = pros_ul.find_elements(By.TAG_NAME, "li")
                    pros = [pro.text.strip() for pro in pros_items if pro.text.strip()]
                    self.logger.info(f"[INFO] ✓ Extracted {len(pros)} pros: {pros}")
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not extract pros: {e}")
                
                # Extract Cons using the actual HTML structure
                cons = []
                try:
                    self.logger.info("[DEBUG] Attempting to find Cons...")
                    
                    # Find h3 with "Cons" text
                    cons_h3 = pros_cons_section.find_element(By.XPATH, ".//h3[contains(text(), 'Cons')]")
                    # Get the parent div that contains both h3 and ul
                    cons_container = cons_h3.find_element(By.XPATH, "ancestor::div[contains(@class, '_1ivmml5yu')][1]")
                    # Get the ul
                    cons_ul = cons_container.find_element(By.XPATH, ".//ul[contains(@class, '_6h1tsc2')]")
                    cons_items = cons_ul.find_elements(By.TAG_NAME, "li")
                    cons = [con.text.strip() for con in cons_items if con.text.strip()]
                    self.logger.info(f"[INFO] ✓ Extracted {len(cons)} cons: {cons}")
                except Exception as e:
                    self.logger.error(f"[ERROR] Could not extract cons: {e}")
                
                # Yield pros and cons
                self.logger.info(f"[INFO] Yielding {len(pros)} pros and {len(cons)} cons")
                for pro in pros:
                    yield {
                        "modelName": actual_model_name,
                        "prosConsType": "Pro",
                        "prosConsContent": pro
                    }
                
                for con in cons:
                    yield {
                        "modelName": actual_model_name,
                        "prosConsType": "Con",
                        "prosConsContent": con
                    }
            else:
                self.logger.info("[INFO] Pros/cons section not available on this page - skipping")
            
            self.logger.info("[INFO] ========== COMPLETED PROS/CONS EXTRACTION ==========")
        except Exception as e:
            # Don't fail the entire spider if pros/cons is missing
            self.logger.warning(f"[WARNING] Pros/cons extraction skipped: {e}")
            self.logger.info("[INFO] ========== PROS/CONS EXTRACTION SKIPPED ==========")
            # Continue with the rest of the spider

        # Scroll to Variants section and extract variant URLs
        variant_urls = []
        try:
            # Wait for variants section to be visible - the specific div containing variant links
            variants_section = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, '_1ivmml5yu') and contains(@class, '_1ivmml517l')]//a[contains(@href, '/features-and-specs')]"))
            )
            
            # Find all variant links within the specific variants container
            # This excludes links that are outside the variant list (like generic model links)
            variant_links = driver.find_elements(By.XPATH, "//div[contains(@class, '_1ivmml5yu') and contains(@class, '_1ivmml517l')]//a[contains(@href, '/features-and-specs')]")
            
            for link in variant_links:
                href = link.get_attribute('href')
                # Additional check: variant URLs should have at least 5 path segments (protocol, empty, domain, brand, model, variant, features-and-specs)
                # This filters out generic model URLs like /mahindra/scorpio/features-and-specs
                if href and href not in variant_urls and href.count('/') >= 6:
                    variant_urls.append(href)
                    self.logger.info(f"[INFO] Found variant URL: {href}")
        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract variant URLs: {e}")

        # Store variant URLs in meta for later processing
        response.meta['variant_urls'] = variant_urls
        response.meta['model_name'] = actual_model_name
        response.meta['brand_name'] = brand_name
        
        # Debug: Save variant URLs to file
        try:
            import os
            debug_dir = "debug_output"
            os.makedirs(debug_dir, exist_ok=True)
            safe_model_name = model_name.replace(' ', '_').replace('/', '_')
            debug_file = os.path.join(debug_dir, f"variant_urls_{safe_model_name}.txt")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(f"Model: {model_name}\n")
                f.write(f"Total variant URLs found: {len(variant_urls)}\n\n")
                for idx, url in enumerate(variant_urls, 1):
                    f.write(f"{idx}. {url}\n")
            self.logger.info(f"[DEBUG] Saved {len(variant_urls)} variant URLs to {debug_file}")
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not save variant URLs to debug file: {e}")

        # Scroll to FAQs section
        try:
            faq_heading = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h2[contains(text(), 'Frequently Asked Questions')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", faq_heading)
            time.sleep(2)
            self.logger.info("[INFO] Scrolled to FAQ section")
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not scroll to FAQ section: {e}")

        # Extract FAQs
        faqs = []
        try:
            faq_accordions = driver.find_elements(By.XPATH, "//div[@data-testid='accordion']")
            self.logger.info(f"[INFO] Found {len(faq_accordions)} FAQ items")
            
            for faq in faq_accordions:
                try:
                    # Get question
                    question_elem = faq.find_element(By.XPATH, ".//span[@data-testid='accordion-header-title-text']")
                    question = question_elem.text.strip()
                    
                    # Click to expand
                    button = faq.find_element(By.XPATH, ".//button[@data-testid='accordion-header-button']")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(1)
                    
                    # Get answer
                    answer_elem = faq.find_element(By.XPATH, ".//div[@data-testid='accordion-content']//p")
                    answer = answer_elem.text.strip()
                    
                    faqs.append({
                        "modelName": actual_model_name,
                        "faqQuestion": question,
                        "faqAnswer": answer
                    })
                    
                    self.logger.info(f"[INFO] Extracted FAQ: {question[:50]}...")
                except Exception as e:
                    self.logger.warning(f"[WARNING] Could not extract FAQ item: {e}")
                    continue
        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract FAQs: {e}")

        # Yield FAQs
        for faq in faqs:
            yield faq
