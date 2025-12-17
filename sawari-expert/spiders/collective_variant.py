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


class CarExpertVariantSpider(scrapy.Spider):
    name = "collective_variant"
    allowed_domains = ["carexpert.com.au"]
    
    # Default values (can be overridden by command-line arguments)
    start_urls = [
        "https://www.carexpert.com.au/ford/ranger/2026-xl-jo5ga5kk20250910"
    ]
    
    # URL-based mapping for model names and variants
    url_mapping = {
        "ford/ranger/2026-xl-jo5ga5kk20250910": {
            "modelName": "Ranger",
            "variantName": "2.0L, 6-speed auto, 4-door Cab Chassis, Diesel, RWD"
        },
        # Add more mappings as needed
        # "make/model/variant-identifier": {
        #     "modelName": "Make Model",
        #     "variantName": "Variant Name"
        # }
    }
    
    def __init__(self, start_url=None, mapping_key=None, model_name=None, variant_name=None, *args, **kwargs):
        super(CarExpertVariantSpider, self).__init__(*args, **kwargs)
        
        # Override start_urls if provided via command line
        if start_url:
            self.start_urls = [start_url]
            self.logger.info(f"[INIT] Using provided start_url: {start_url}")
        
        # Override url_mapping if all mapping parameters are provided
        if mapping_key and model_name and variant_name:
            self.url_mapping = {
                mapping_key: {
                    "modelName": model_name,
                    "variantName": variant_name
                }
            }
            self.logger.info(f"[INIT] Using provided mapping: {mapping_key} -> {model_name} | {variant_name}")
    
    custom_settings = {
        'ITEM_PIPELINES': {
            'sawari-expert.pipelines.CarExpertVariantJsonPipeline': 306,
            'sawari-expert.pipelines.CarExpertVariantCsvPipeline': 307,
            'sawari-expert.pipelines.CarExpertFeatureJsonPipeline': 308,
            'sawari-expert.pipelines.CarExpertFeatureCsvPipeline': 309,
            'sawari-expert.pipelines.CarExpertSpecificationJsonPipeline': 310,
            'sawari-expert.pipelines.CarExpertSpecificationCsvPipeline': 311,
        }
    }

    def get_model_and_variant_from_url(self, url):
        """Extract model and variant names from URL using dictionary mapping."""
        try:
            # Remove domain and trailing slashes
            url_path = url.replace("https://www.carexpert.com.au/", "").rstrip('/')
            
            # Try exact match in mapping dictionary
            for key, mapping in self.url_mapping.items():
                if key in url_path:
                    self.logger.info(f"[MAPPING] Match found for: {key}")
                    return mapping["modelName"], mapping["variantName"]
            
            # No mapping found - return None to skip this URL
            self.logger.error(f"[MAPPING ERROR] No mapping found for URL: {url}")
            return None, None
            
        except Exception as e:
            self.logger.error(f"[MAPPING ERROR] {e}")
            return None, None

    def start_requests(self):
        for url in self.start_urls:
            yield SeleniumRequest(
                url=url,
                callback=self.parse_variant,
                wait_time=20,
                dont_filter=True,
                meta={'dont_cache': True}
            )

    def parse_variant(self, response):
        driver = response.meta.get("driver")
        
        if not driver:
            self.logger.error("[ERROR] WebDriver not found")
            return

        # Extract model and variant name using dictionary mapping
        model_name, variant_name = self.get_model_and_variant_from_url(response.url)
        self.logger.info(f"[INFO] Model: {model_name}")
        self.logger.info(f"[INFO] Variant: {variant_name}")

        # Yield variant information
        yield {
            "modelName": model_name,
            "makeYear": "2025",
            "variantName": variant_name,
            "variantPrice": "",
            "variantFuelType": "",
            "variantSeatingCapacity": "",
            "variantType": "base",
            "variantIsPopular": "",
            "variantMileage": ""
        }

        # Open debug file for this variant
        import os
        debug_dir = "debug_output"
        os.makedirs(debug_dir, exist_ok=True)
        safe_variant_name = variant_name.replace(' ', '_').replace('/', '_')
        debug_file = os.path.join(debug_dir, f"variant_extraction_{safe_variant_name}.txt")
        debug_log = open(debug_file, 'w', encoding='utf-8')
        debug_log.write(f"Variant: {variant_name}\n")
        debug_log.write(f"URL: {response.url}\n\n")
        
        # Also create a detailed content extraction file
        content_file = os.path.join(debug_dir, f"content_extracted_{safe_variant_name}.txt")
        content_log = open(content_file, 'w', encoding='utf-8')
        content_log.write(f"=== CONTENT EXTRACTION LOG ===\n")
        content_log.write(f"Variant: {variant_name}\n")
        content_log.write(f"Model: {model_name}\n")
        content_log.write(f"URL: {response.url}\n\n")

        # Category mapping based on MAIN HEADERS (not sub-headings)
        # Features mapping - from Other Site Category to Your Site Feature Category
        feature_category_mapping = {
            "convenience": "Comfort & Convenience",
            "instrumentation": "Instrumentation",
            "body exterior": "Exterior",
            "doors": "Doors, Windows, Mirrors & Wipers",
            "lights": "Lighting",
            "visibility": "Doors, Windows, Mirrors & Wipers",
            "audio": "Entertainment, Information & Communication",
            "interior trim": "Seats & Upholstery",
            "safety": "Safety",
            "seats": "Seats & Upholstery",
            "storage": "Storage",
            "ventilation": "Comfort & Convenience",
            "locks": "Locks & Security",
            "service": "Manufacturer Warranty"
        }

        # Specifications mapping - from Other Site Category to Your Site Specification Category
        spec_category_mapping = {
            "engine": "Engine & Transmission",
            "performance": "Engine & Transmission",
            "transmission": "Engine & Transmission",
            "brakes": "Suspensions, Brakes, Steering & Tyres",
            "steering": "Suspensions, Brakes, Steering & Tyres",
            "suspension": "Suspensions, Brakes, Steering & Tyres",
            "wheels": "Suspensions, Brakes, Steering & Tyres",
            "dimensions": "Dimensions & Weight",
            "weights": "Dimensions & Weight",
            "fuel": "Capacity",
            "cargo area": "Capacity",
            
        }
        
        # Define which standardized categories are features vs specifications
        feature_categories = {
            "Comfort & Convenience",
            "Instrumentation",
            "Exterior",
            "Doors, Windows, Mirrors & Wipers",
            "Lighting",
            "Entertainment, Information & Communication",
            "Seats & Upholstery",
            "Safety",
            "Storage",
            "Ventilation",
            "Locks & Security"
        }
        
        specification_categories = {
            "Engine & Transmission",
            "Suspensions, Brakes, Steering & Tyres",
            "Dimensions & Weight",
            "Capacity",
            "Manufacturer Warranty"
        }

        # Save page source for debugging
        try:
            page_source_file = os.path.join(debug_dir, f"page_source_{safe_variant_name}.html")
            with open(page_source_file, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            self.logger.info(f"[DEBUG] Saved page source to {page_source_file}")
        except Exception as e:
            self.logger.warning(f"[WARNING] Could not save page source: {e}")

        # Extract all specification sections directly
        try:
            # Find all specification sections with IDs like 'vehicle-spec-*'
            spec_sections = driver.find_elements(By.XPATH, "//div[starts-with(@id, 'vehicle-spec-')]")
            self.logger.info(f"[DEBUG] Found {len(spec_sections)} specification sections on variant page")
            debug_log.write(f"Total specification sections found: {len(spec_sections)}\n\n")
            
            for section_idx, section in enumerate(spec_sections):
                try:
                    # Get section ID (e.g., 'vehicle-spec-driver-modes')
                    section_id = section.get_attribute('id')
                    
                    # Extract sub-heading from ID (e.g., 'driver-modes' -> 'Driver Modes')
                    sub_heading = section_id.replace('vehicle-spec-', '').replace('-', ' ').title()
                    
                    self.logger.info(f"[INFO] Processing section: {section_id} ({sub_heading})")
                    debug_log.write(f"Section {section_idx + 1}: {section_id} ({sub_heading})\n")
                    
                    # Scroll to section
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", section)
                    time.sleep(0.5)
                    
                    # Find the MAIN CATEGORY from the accordion button
                    # The structure is: <button><div>Category Name</div></button>
                    # followed by sections with vehicle-spec-* IDs
                    main_category = None
                    try:
                        # Look for the preceding button element that contains the category
                        # The button has aria-expanded and aria-controls attributes
                        category_button = section.find_element(
                            By.XPATH, 
                            "preceding::button[contains(@class, '_1ivmml5') and @aria-expanded][1]"
                        )
                        # Get the text from the div inside the button
                        category_div = category_button.find_element(By.XPATH, ".//div")
                        main_category = category_div.text.strip()
                        debug_log.write(f"  Main Category (from button): {main_category}\n")
                        self.logger.info(f"[DEBUG] Main category from button: {main_category}")
                    except Exception as e:
                        debug_log.write(f"  Could not find category button: {e}\n")
                        pass
                    
                    # Fallback: if button not found, try other methods
                    if not main_category:
                        try:
                            # Look for parent section with h2
                            parent_section = section.find_element(By.XPATH, "ancestor::section[1]")
                            category_header = parent_section.find_element(By.XPATH, "./h2")
                            main_category = category_header.text.strip()
                            debug_log.write(f"  Main Category (from parent section h2): {main_category}\n")
                        except:
                            pass
                    
                    # Final fallback: use sub-heading as category
                    if not main_category or not main_category.strip():
                        main_category = sub_heading
                        debug_log.write(f"  Main Category (fallback to sub-heading): {main_category}\n")
                    
                    # Normalize main_category for mapping (lowercase, remove special chars)
                    main_category_normalized = main_category.lower().strip()
                    
                    # Map the MAIN CATEGORY (not sub-heading) to a standardized category
                    standardized_category = None
                    is_feature = False
                    
                    # Try exact match first
                    if main_category_normalized in feature_category_mapping:
                        standardized_category = feature_category_mapping[main_category_normalized]
                        is_feature = True
                    elif main_category_normalized in spec_category_mapping:
                        standardized_category = spec_category_mapping[main_category_normalized]
                        is_feature = False
                    else:
                        # Try partial matching with keywords
                        found = False
                        for key, value in feature_category_mapping.items():
                            if key in main_category_normalized or main_category_normalized in key:
                                standardized_category = value
                                is_feature = True
                                found = True
                                break
                        
                        if not found:
                            for key, value in spec_category_mapping.items():
                                if key in main_category_normalized or main_category_normalized in key:
                                    standardized_category = value
                                    is_feature = False
                                    found = True
                                    break
                        
                        if not found:
                            self.logger.warning(f"[WARNING] Main category '{main_category}' not mapped!")
                            debug_log.write(f"  -> NOT MAPPED! Defaulting to Other\n")
                            standardized_category = "Other"
                            is_feature = True
                    
                    # Verify feature vs specification based on the standardized category
                    if standardized_category in feature_categories:
                        is_feature = True
                    elif standardized_category in specification_categories:
                        is_feature = False
                    
                    category_type = 'Feature' if is_feature else 'Specification'
                    self.logger.info(f"[DEBUG] Main category '{main_category}' -> '{standardized_category}' ({category_type})")
                    debug_log.write(f"  -> Mapped to: {standardized_category} ({category_type})\n")
                    debug_log.write(f"  Sub-heading: {sub_heading}\n")
                    
                    # Find all key-value pairs in this section
                    # Based on actual HTML: <p><span>Key</span>:<!-- --> <span>value</span></p>
                    pairs = section.find_elements(By.XPATH, ".//p[.//span]")
                    debug_log.write(f"  Found {len(pairs)} pairs in this section\n")
                    
                    for pair in pairs:
                        try:
                            # Get all spans in the paragraph
                            spans = pair.find_elements(By.TAG_NAME, "span")
                            
                            if len(spans) >= 2:
                                # First span is the key, second (or last) is the value
                                name = spans[0].text.strip()
                                value = spans[-1].text.strip()
                                
                                # Skip if name or value is empty
                                if not name or not value:
                                    continue
                                
                                debug_log.write(f"    Extracted: {name} = {value}\n")
                                
                                # Yield feature or specification based on standardized category
                                if is_feature:
                                    feature_item = {
                                        "type": "feature",
                                        "modelName": model_name,
                                        "variantName": variant_name,
                                        "featureCategoryName": standardized_category,
                                        "featureName": name,
                                        "featureValue": value
                                    }
                                    yield feature_item
                                    self.logger.info(f"[FEATURE] {variant_name} | {standardized_category} | {name} = {value}")
                                    content_log.write(f"FEATURE | {standardized_category} | {name} | {value}\n")
                                    content_log.write(f"  Full Item: {feature_item}\n\n")
                                else:
                                    spec_item = {
                                        "type": "specification",
                                        "modelName": model_name,
                                        "variantName": variant_name,
                                        "specificationCategoryName": standardized_category,
                                        "specificationName": name,
                                        "specificationValue": value
                                    }
                                    yield spec_item
                                    self.logger.info(f"[SPEC] {variant_name} | {standardized_category} | {name} = {value}")
                                    content_log.write(f"SPECIFICATION | {standardized_category} | {name} | {value}\n")
                                    content_log.write(f"  Full Item: {spec_item}\n\n")
                            else:
                                debug_log.write(f"    Skipped pair (not enough spans): {pair.text}\n")
                        except Exception as e:
                            debug_log.write(f"    ERROR extracting pair: {e}\n")
                            continue
                        
                except Exception as e:
                    self.logger.warning(f"[WARNING] Error processing section: {e}")
                    debug_log.write(f"ERROR processing section: {e}\n")
                    continue
                    
        except Exception as e:
            self.logger.error(f"[ERROR] Could not extract features/specifications: {e}")
            debug_log.write(f"\nFATAL ERROR: {e}\n")
        
        finally:
            content_log.close()
            debug_log.close()
            self.logger.info(f"[DEBUG] Saved variant extraction debug to {debug_file}")
            self.logger.info(f"[DEBUG] Saved content extraction log to {content_file}")
