import csv
import os
import re
import time

import scrapy
from scrapy_selenium import SeleniumRequest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class CarexpertFeaturesSpecsSpider(scrapy.Spider):
    """
    Spider for extracting Features and Specifications from CarExpert in row-based format
    Creates Features.csv and Specifications.csv with each row being a feature/spec for a variant
    Example URL: https://www.carexpert.com.au/mg/mg-s5-ev
    """

    name = "carexpert_features_specs"
    allowed_domains = ["carexpert.com.au"]

    def __init__(self, start_url=None, *args, **kwargs):
        super(CarexpertFeaturesSpecsSpider, self).__init__(*args, **kwargs)

        if start_url:
            self.start_urls = [start_url]
        else:
            # Default URL
            self.start_urls = ["https://www.carexpert.com.au/ford/ranger"]

        # Extract brand and model from URL
        url = self.start_urls[0]
        url_parts = url.rstrip("/").split("/")

        if len(url_parts) >= 2:
            self.brand_name = (
                url_parts[-2].upper() if len(url_parts) >= 2 else "Unknown"
            )
            self.model_name = (
                url_parts[-1].replace("-", " ").title()
                if len(url_parts) >= 1
                else "Unknown"
            )
        else:
            self.brand_name = "Ford"
            self.model_name = "Ranger"

        # Output directory
        self.output_dir = f"Output/{self.brand_name}/{self.model_name}"
        os.makedirs(self.output_dir, exist_ok=True)

        # Data storage
        self.features_rows = []
        self.specs_rows = []
        self.make_year = 2025

        self.logger.info(f"Initialized spider for: {self.brand_name} {self.model_name}")
        self.logger.info(f"Output directory: {self.output_dir}")

    custom_settings = {
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

        # Step 1: Find all variant links
        variant_links = self.find_variant_links(driver)

        if not variant_links:
            self.logger.error("No variant links found!")
            return

        self.logger.info(f"Found {len(variant_links)} variants to process")

        # Step 2: Click each variant and extract features/specs
        for idx, (variant_name, variant_url) in enumerate(variant_links, 1):
            self.logger.info("=" * 80)
            self.logger.info(
                f"Processing Variant {idx}/{len(variant_links)}: {variant_name}"
            )
            self.logger.info("=" * 80)

            # Navigate to variant page
            try:
                driver.get(variant_url)
                time.sleep(3)

                # Extract features and specs for this variant
                self.extract_variant_features_specs(driver, variant_name)

            except Exception as e:
                self.logger.error(f"Error processing variant {variant_name}: {e}")
                import traceback

                self.logger.error(traceback.format_exc())

        # Step 3: Save to CSV files
        self.save_to_csv()

        self.logger.info("✓ Completed scraping features and specifications")

    def find_variant_links(self, driver):
        """Find all variant links on the main page"""
        variant_links = []

        try:
            # Scroll to variants section
            try:
                variants_heading = driver.find_element(
                    By.XPATH, "//h2[contains(text(), 'Available Variants')]"
                )
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                    variants_heading,
                )
                time.sleep(2)
            except:
                self.logger.warning("Could not find 'Available Variants' heading")

            # Find all variant links
            variant_elements = driver.find_elements(
                By.XPATH, "//a[contains(@href, '/features-and-specs')]"
            )

            self.logger.info(f"Found {len(variant_elements)} variant links")

            for variant_elem in variant_elements:
                try:
                    # Get variant name from h2 tag
                    variant_name_elem = variant_elem.find_element(By.XPATH, ".//h2")
                    variant_name = variant_name_elem.text.strip()

                    # Get URL
                    variant_url = variant_elem.get_attribute("href")

                    if variant_name and variant_url:
                        variant_links.append((variant_name, variant_url))
                        self.logger.info(f"  ✓ {variant_name}: {variant_url}")

                except Exception as e:
                    self.logger.warning(f"Could not extract variant info: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error finding variant links: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

        return variant_links

    def extract_variant_features_specs(self, driver, variant_name):
        """Extract features and specifications from a variant page"""

        try:
            # Wait for the page to load
            time.sleep(3)

            # Scroll through sections to load all content
            self.scroll_to_specs_section(driver)

            # First, try to extract variant names from column headers
            variant_names_in_columns = self.extract_variant_names_from_headers(driver)

            if not variant_names_in_columns:
                # Fallback to using the passed variant_name
                self.logger.warning(
                    "Could not extract variant names from headers, using passed variant_name"
                )
                variant_names_in_columns = [variant_name]

            self.logger.info(
                f"Variant names found in columns: {variant_names_in_columns}"
            )

            # Find all feature/spec sections
            sections = driver.find_elements(
                By.XPATH, '//div[contains(@class, "_1egt6kt9")]'
            )

            self.logger.info(f"Found {len(sections)} feature/spec sections")

            for section in sections:
                try:
                    section_id = section.get_attribute("id")

                    # Find all variant columns in this section
                    variant_columns = section.find_elements(
                        By.XPATH, './/div[contains(@class, "_1egt6kth")]'
                    )

                    self.logger.info(
                        f"Processing section with {len(variant_columns)} columns"
                    )

                    # Iterate through all columns (all variants)
                    for column_idx, variant_column in enumerate(variant_columns):
                        try:
                            # Use the correct variant name for this column
                            if column_idx < len(variant_names_in_columns):
                                current_variant_name = variant_names_in_columns[
                                    column_idx
                                ]
                            else:
                                current_variant_name = (
                                    f"{variant_name} (Column {column_idx + 1})"
                                )

                            # Get the feature/spec category name
                            title_elem = variant_column.find_element(
                                By.XPATH, './/div[contains(@class, "_1ivmml5uy")]'
                            )
                            category_name = title_elem.text.strip()

                            # Get all specifications under this category
                            content_div = variant_column.find_element(
                                By.XPATH, './/div[contains(@class, "_1ivmml5ur")]'
                            )

                            spec_paragraphs = content_div.find_elements(
                                By.XPATH, ".//p"
                            )

                            for p in spec_paragraphs:
                                spans = p.find_elements(By.XPATH, ".//span")

                                if len(spans) >= 2:
                                    spec_name = spans[0].text.strip()
                                    spec_value = spans[1].text.strip()

                                    # Remove category prefix from spec name if present
                                    if spec_name.startswith(category_name):
                                        spec_name = spec_name[
                                            len(category_name) :
                                        ].strip()

                                    # Determine if this is a feature or specification
                                    if spec_value.lower() in ["yes", "no"]:
                                        # This is a feature
                                        feature_row = {
                                            "modelName": self.model_name,
                                            "makeYear": self.make_year,
                                            "variantName": current_variant_name,
                                            "featureCategoryName": category_name,
                                            "featureName": spec_name,
                                            "featureValue": spec_value,
                                            "featureIsHighlighted": "",
                                        }
                                        self.features_rows.append(feature_row)
                                    else:
                                        # This is a specification
                                        spec_row = {
                                            "modelName": self.model_name,
                                            "makeYear": self.make_year,
                                            "variantName": current_variant_name,
                                            "specificationCategoryName": category_name,
                                            "specificationName": spec_name,
                                            "specificationValue": spec_value,
                                        }
                                        self.specs_rows.append(spec_row)

                        except Exception as e:
                            self.logger.warning(
                                f"Error processing column {column_idx}: {e}"
                            )
                            continue

                except Exception as e:
                    self.logger.warning(f"Error processing section: {e}")
                    continue

            self.logger.info(
                f"✓ Extracted {len(self.features_rows)} features and {len(self.specs_rows)} specs so far"
            )

        except Exception as e:
            self.logger.error(f"Error extracting features/specs: {e}")
            import traceback

            self.logger.error(traceback.format_exc())

    def extract_variant_names_from_headers(self, driver):
        """Extract variant names from column headers on the comparison page"""
        variant_names = []

        try:
            # Try to find variant name headers - these might be in different locations
            # Try common patterns for variant headers

            # Pattern 1: Look for h1 or h2 elements that might contain variant names
            header_elements = driver.find_elements(
                By.XPATH,
                '//div[contains(@class, "_1egt6kth")]//h1 | //div[contains(@class, "_1egt6kth")]//h2',
            )

            if header_elements:
                for header in header_elements:
                    variant_text = header.text.strip()
                    if variant_text:
                        variant_names.append(variant_text)
                        self.logger.info(
                            f"Found variant name in header: {variant_text}"
                        )

            # Pattern 2: If no headers found, look for variant info in the page structure
            if not variant_names:
                # Try to find variant selectors or buttons that might indicate variant names
                variant_buttons = driver.find_elements(
                    By.XPATH,
                    '//button[contains(@class, "variant") or contains(@aria-label, "variant")]',
                )

                for button in variant_buttons:
                    variant_text = button.text.strip()
                    if variant_text and variant_text not in variant_names:
                        variant_names.append(variant_text)
                        self.logger.info(
                            f"Found variant name in button: {variant_text}"
                        )

            # Pattern 3: Look for any strong or bold text at the top of columns
            if not variant_names:
                strong_elements = driver.find_elements(
                    By.XPATH, '//div[contains(@class, "_1egt6kth")]//strong'
                )

                for strong in strong_elements[
                    :5
                ]:  # Limit to first few to avoid grabbing spec names
                    variant_text = strong.text.strip()
                    if variant_text and len(variant_text) > 3:  # Avoid very short text
                        variant_names.append(variant_text)
                        self.logger.info(
                            f"Found variant name in strong element: {variant_text}"
                        )

        except Exception as e:
            self.logger.warning(f"Error extracting variant names from headers: {e}")

        return variant_names

    def scroll_to_specs_section(self, driver):
        """Scroll to the specifications section to ensure all content loads"""
        try:
            # Try to find and scroll to a specs section
            specs_sections = driver.find_elements(
                By.XPATH,
                '//h2[contains(text(), "Convenience") or contains(text(), "Safety") or contains(text(), "Specifications")]',
            )

            if specs_sections:
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'start'});",
                    specs_sections[0],
                )
                time.sleep(2)

                # Scroll down to load more content
                for _ in range(3):
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(1)

        except Exception as e:
            self.logger.warning(f"Could not scroll to specs section: {e}")

    def save_to_csv(self):
        """Save features and specifications to CSV files in row-based format"""

        # Create Features.csv
        if self.features_rows:
            features_path = os.path.join(self.output_dir, "Features.csv")

            with open(features_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "modelName",
                    "makeYear",
                    "variantName",
                    "featureCategoryName",
                    "featureName",
                    "featureValue",
                    "featureIsHighlighted",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.features_rows)

            self.logger.info(
                f"✓ Created {features_path} with {len(self.features_rows)} rows"
            )
        else:
            self.logger.warning("No features data to save")

        # Create Specifications.csv
        if self.specs_rows:
            specs_path = os.path.join(self.output_dir, "Specifications.csv")

            with open(specs_path, "w", newline="", encoding="utf-8") as f:
                fieldnames = [
                    "modelName",
                    "makeYear",
                    "variantName",
                    "specificationCategoryName",
                    "specificationName",
                    "specificationValue",
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.specs_rows)

            self.logger.info(f"✓ Created {specs_path} with {len(self.specs_rows)} rows")
        else:
            self.logger.warning("No specifications data to save")

        # Log summary
        self.logger.info("=" * 80)
        self.logger.info("SUMMARY")
        self.logger.info("=" * 80)
        self.logger.info(f"Brand: {self.brand_name}")
        self.logger.info(f"Model: {self.model_name}")
        self.logger.info(f"Total Feature Rows: {len(self.features_rows)}")
        self.logger.info(f"Total Specification Rows: {len(self.specs_rows)}")
        self.logger.info(f"Output directory: {self.output_dir}")
        self.logger.info("=" * 80)
