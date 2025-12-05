#!/usr/bin/env python3
"""
Script to update vehicle variants CSV file from a JSON mapping file.

Features:
- Replaces variantName values based on JSON mapping
- Sets variantType to 'Top' for highest priced variant, 'Base' for others
- Randomly assigns variantIsPopular (True/False)
"""

import os
import csv
import json
import random
import re
from typing import Dict, List

brand_name = 'Maruti'
model_name = 'Ciaz'
# Configuration - Update these paths as needed
CSV_BASE_PATH = "/home/ares-am/Projects/BNT/scrapy/Output/Maruti/Ciaz"
JSON_MAPPING_FILE = "/home/ares-am/Projects/BNT/scrapy/utils/variant_mapping.json"  # Default JSON mapping file
OUTPUT_SUFFIX = ""  # Will create Variants_updated.csv


class VariantUpdater:
    """Class to handle updating variants from JSON mapping."""

    def __init__(self, json_mapping_path: str = JSON_MAPPING_FILE):
        """Initialize with JSON mapping file."""
        self.mapping = self.load_json_mapping(json_mapping_path)

    def load_json_mapping(self, json_path: str) -> Dict[str, str]:
        """Load the JSON mapping file."""
        if not os.path.exists(json_path):
            print(f"⚠️  Warning: JSON mapping file not found: {json_path}")
            print("✓ Will only update variantType and variantIsPopular")
            return {}

        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                mapping = json.load(f)
                print(f"✓ Loaded {len(mapping)} variant name mappings")
                return mapping
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON file: {e}")
            return {}

    def extract_price_value(self, price_str: str) -> float:
        """Extract numeric price value from price string."""
        if not price_str:
            return 0.0

        # Remove currency symbols and convert to float
        # Handles formats like: "5.35 Lakh", "10.5 Lakh", "1.2 Crore"
        price_str = price_str.strip().upper()

        # Extract number
        match = re.search(r'(\d+\.?\d*)', price_str)
        if not match:
            return 0.0

        value = float(match.group(1))

        # Convert to lakhs for comparison
        if 'CRORE' in price_str or 'CR' in price_str:
            value = value * 100  # 1 Crore = 100 Lakhs

        return value

    def find_highest_price_variant(self, rows: List[Dict]) -> str:
        """Find the variant name with highest price."""
        max_price = 0.0
        max_variant = ""

        for row in rows:
            price = self.extract_price_value(row.get('variantPrice', ''))
            variant_name = row.get('variantName', '')

            if price > max_price:
                max_price = price
                max_variant = variant_name

        return max_variant

    def update_variant_name(self, original_name: str) -> str:
        """Update variant name using mapping."""
        # Check if exact match exists in mapping
        if original_name in self.mapping:
            return self.mapping[original_name]

        # Check case-insensitive match
        original_lower = original_name.lower()
        for key, value in self.mapping.items():
            if key.lower() == original_lower:
                return value

        # No mapping found, return original
        return original_name

    def process_csv(self, csv_path: str, output_path: str):
        """Process the CSV file and update variants."""
        print(f"\n{'='*60}")
        print(f"Processing: {csv_path}")
        print(f"{'='*60}")

        # Check if file exists
        if not os.path.exists(csv_path):
            print(f"❌ Error: CSV file not found: {csv_path}")
            return

        # Read CSV
        rows = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        print(f"Total rows: {len(rows)}")

        # Find highest priced variant
        highest_variant = self.find_highest_price_variant(rows)
        print(f"Highest priced variant: {highest_variant}")

        # Update rows
        updated_names = 0
        updated_types = 0
        updated_popularity = 0

        for row in rows:
            original_variant = row.get('variantName', '')

            # Update variant name
            new_variant_name = self.update_variant_name(original_variant)
            if new_variant_name != original_variant:
                row['variantName'] = new_variant_name
                updated_names += 1

            # Update variant type (Top for highest price, Base for others)
            if original_variant == highest_variant:
                row['variantType'] = 'top'
            else:
                row['variantType'] = 'base'
            updated_types += 1

            # Update variant popularity (random True/False)
            row['variantIsPopular'] = random.choice(['True', 'False'])
            updated_popularity += 1

        # Write updated CSV
        print(f"\nWriting updated CSV to: {output_path}")

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n{'='*60}")
        print(f"Update Summary:")
        print(f"{'='*60}")
        print(f"✓ Variant names updated: {updated_names}")
        print(f"✓ Variant types updated: {updated_types} (1 Top, {updated_types-1} Base)")
        print(f"✓ Popularity randomly assigned: {updated_popularity}")
        print(f"✅ CSV processing complete!")


def find_variant_csv_files(base_path: str) -> List[str]:
    """Find all Variants.csv files in the output directory."""
    csv_files = []

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file == 'Variants.csv':
                csv_files.append(os.path.join(root, file))

    return csv_files


def process_single_csv(csv_path: str, json_mapping_path: str = JSON_MAPPING_FILE):
    """Process a single CSV file."""
    # Create output path
    csv_dir = os.path.dirname(csv_path)
    csv_name = os.path.basename(csv_path)
    name_without_ext = os.path.splitext(csv_name)[0]
    output_path = os.path.join(csv_dir, f"{name_without_ext}{OUTPUT_SUFFIX}.csv")

    # Process
    updater = VariantUpdater(json_mapping_path)
    updater.process_csv(csv_path, output_path)


def main():
    """Main function."""
    print("="*60)
    print("Vehicle Variant CSV Updater")
    print("="*60)

    # Use default JSON mapping file and CSV path
    json_mapping_path = JSON_MAPPING_FILE
    csv_path = os.path.join(CSV_BASE_PATH, "Variants.csv")

    # Process the CSV
    print(f"\n📄 JSON Mapping: {json_mapping_path}")
    print(f"📄 CSV File: {csv_path}")

    process_single_csv(csv_path, json_mapping_path)


if __name__ == "__main__":
    main()
