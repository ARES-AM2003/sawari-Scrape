# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import os
import json
import csv

# Global variables for brand and model names


brand_name = 'Mahendra'
model_name = 'Thar'
# Output directory - all files will be saved here
OUTPUT_DIR = f'Output/{brand_name}/{model_name}'

def set_brand_model(brand, model):
    """Set global brand and model names"""
    global brand_name, model_name
    brand_name = brand
    model_name = model


class SawariexpertPipeline:
    def process_item(self, item, spider):
        return item


class ModelInfoJsonPipeline:
    def open_spider(self, spider):
        # Set global variables from spider attributes
        global brand_name, model_name
        brand_name = getattr(spider, 'brand_name', 'Unknown')
        model_name = getattr(spider, 'model_name', 'Unknown')

        # Create output directory
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Models.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "modelName" in item and "bodyType" in item and "ratingCategoryName" not in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)

class ModelInfoCsvPipeline:
    header = [
        "brandName",
        "modelName",
        "modelDescription",
        "modelTagline",
        "modelIsHiglighted",
        "bodyType"
    ]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Models.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "modelName" in item and "bodyType" in item and "ratingCategoryName" not in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

# Pros Cons Pipelines
class ProsConsInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'ProsCons.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="utf-8") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "prosConsType" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=4)

class ProsConsInfoCsvPipeline:
    header = [
        "modelName",
        "prosConsType",
        "prosConsContent"
    ]

    def open_spider(self, spider):
        import csv
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'ProsCons.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "prosConsType" in item:
            row = {key: item.get(key, "") for key in self.header}
            for key in self.header:
                if key not in row or row[key] is None:
                    row[key] = ""
            self.items.append(row)
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

# Color Options Pipelines
class ColourOptionsInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'ModelColors.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r", encoding="utf-8") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "colourName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=4)

class ColourOptionsInfoCsvPipeline:
    header = [
        "modelName",
        "colourName",
        "hexCode"
    ]

    def open_spider(self, spider):
        import csv
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'ModelColors.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "colourName" in item:
            row = {key: item.get(key, "") for key in self.header}
            for key in self.header:
                if key not in row or row[key] is None:
                    row[key] = ""
            self.items.append(row)
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

class VariantInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Variants.json')

        # Start fresh each time - no appending
        self.items = []
        self.seen_variants = set()  # Track unique variants
        spider.logger.info(f"[VariantInfoJsonPipeline] Starting fresh - will overwrite {self.filename}")

    def process_item(self, item, spider):
        # Create a unique key for deduplication based on modelName and variantName
        if "variantName" in item:
            variant_key = f"{item.get('modelName', '')}_{item.get('variantName', '')}"
            if variant_key not in self.seen_variants:
                self.seen_variants.add(variant_key)
                self.items.append(dict(item))
                spider.logger.info(f"[VariantInfoJsonPipeline] Added variant: {item.get('variantName', '')}")
            else:
                spider.logger.debug(f"[VariantInfoJsonPipeline] Skipping duplicate variant: {item.get('variantName', '')}")
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)
        spider.logger.info(f"[VariantInfoJsonPipeline] Saved {len(self.items)} unique variants to {self.filename}")

class VariantInfoCsvPipeline:
    header = [
    "modelName",
    "makeYear",
    "variantName",
    "variantPrice",
    "variantFuelType",
    "variantSeatingCapacity",
    "variantType",
    "variantIsPopular",
    "variantMileage"
]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Variants.csv')

        # Check if file exists to determine if we need to write header
        file_exists = os.path.exists(self.filename)

        # Use append mode to add new variants without overwriting
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)

        # Only write header if file is new
        if not file_exists:
            self.writer.writeheader()
            spider.logger.info(f"[VariantInfoCsvPipeline] Created new file: {self.filename}")
        else:
            spider.logger.info(f"[VariantInfoCsvPipeline] Appending to existing file: {self.filename}")

        # Load existing variants to avoid duplicates
        self.seen_variants = set()
        if file_exists:
            with open(self.filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    variant_key = f"{row.get('modelName', '')}_{row.get('variantName', '')}"
                    self.seen_variants.add(variant_key)
            spider.logger.info(f"[VariantInfoCsvPipeline] Loaded {len(self.seen_variants)} existing variants")

    def process_item(self, item, spider):
        # Create a unique key for deduplication
        if "variantName" in item:
            variant_key = f"{item.get('modelName', '')}_{item.get('variantName', '')}"

            if variant_key not in self.seen_variants:
                self.seen_variants.add(variant_key)
                self.writer.writerow({key: item.get(key, "") for key in self.header})
                spider.logger.info(f"[VariantInfoCsvPipeline] Wrote variant: {item.get('variantName', 'Unknown')}")
            else:
                spider.logger.warning(f"[VariantInfoCsvPipeline] Skipped duplicate variant: {item.get('variantName', 'Unknown')}")

        return item

    def close_spider(self, spider):
        self.csvfile.close()
        spider.logger.info(f"[VariantInfoCsvPipeline] Closed CSV file: {self.filename}")

# These two pipelines are for specifications
class SpecificationInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Specification.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "specificationCategoryName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)

class SpecificationInfoCsvPipeline:
    header = [
        "modelName",
        "makeYear",
        "variantName",
        "specificationCategoryName",
        "specificationName",
        "specificationValue",
    ]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Specifications.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "specificationName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

# These two pipelines are for features
class FeatureInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Features.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "featureCategoryName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)

class FeatureInfoCsvPipeline:
    header = [
        "modelName",
        "makeYear",
        "variantName",
        "featureCategoryName",
        "featureName",
        "featureValue",
        "featureIsHighlighted"

    ]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Features.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "featureName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

class FaqInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Faqs.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "faqQuestion" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)

class FaqInfoCsvPipeline:
    header = [
        "modelName",
        "faqQuestion",
        "faqAnswer"
    ]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Faqs.csv')
        self.file_exists = os.path.exists(self.filename) and os.path.getsize(self.filename) > 0
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "faqQuestion" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()

class RatingInfoJsonPipeline:
    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Ratings.json')

        if os.path.exists(self.filename):
            with open(self.filename, "r") as f:
                try:
                    self.items = json.load(f)
                except Exception:
                    self.items = []
        else:
            self.items = []

    def process_item(self, item, spider):
        if "ratingCategoryName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        with open(self.filename, "w") as f:
            json.dump(self.items, f, indent=4)

class RatingInfoCsvPipeline:
    header = [
        "modelName",
        "ratingCategoryName",
        "rating"
    ]

    def open_spider(self, spider):
        # Create output directory using global variables
        output_dir = OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)

        self.filename = os.path.join(output_dir, 'Ratings.csv')
        self.file_exists = os.path.exists(self.filename)
        self.csvfile = open(self.filename, "a", newline='', encoding="utf-8")
        self.writer = csv.DictWriter(self.csvfile, fieldnames=self.header)
        if not self.file_exists:
            self.writer.writeheader()
        self.items = []

    def process_item(self, item, spider):
        if "ratingCategoryName" in item:
            self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        for row in self.items:
            self.writer.writerow(row)
        self.csvfile.close()
