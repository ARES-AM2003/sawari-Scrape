#!/usr/bin/env python3
"""
Script to fill missing mileage values in vehicle variant CSV files.
Uses Grok AI via OpenRouter API to fetch missing mileage data with correct units:
- Petrol/Diesel: kmpl
- CNG: km/kg
- Electric/EV: km/charge or km/kWh
Validation with other free models is optional.
"""

import os
import csv
import re
import time
from openai import OpenAI

# ---------------- CONFIG ----------------
INPUT_CSV_PATH = "/home/ares-am/Projects/BNT/scrapy/Output/Mahendra/Thar/Variants.csv"
OUTPUT_CSV_PATH = INPUT_CSV_PATH
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

PRIMARY_MODEL = "x-ai/grok-4.1-fast:free"  # main model
VALIDATION_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free"
]

VALIDATION_ENABLED = False  # toggle validation


class MileageFiller:
    def __init__(self, api_key: str):
        if api_key == "<OPENROUTER_API_KEY>":
            raise ValueError("Please set your OpenRouter API key.")
        self.client = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=api_key)

    def extract_mileage_value(self, text: str, fuel_type: str) -> str | None:
        """Extract numeric mileage with correct unit from AI response."""
        text_lower = text.lower()

        if fuel_type.lower() == "cng":
            # Remove kmpl mentions first
            text_clean = re.sub(r'\d+\.?\d*\s*(kmpl|km/l|km per liter)', '', text_lower)
            match = re.search(r'(\d+\.?\d*)\s*(?:km/kg|km per kg|kilometers per kg|kmkg)', text_clean)
            return f"{match.group(1)} km/kg" if match else None

        elif fuel_type.lower() in ["electric", "ev", "battery"]:
            # EV mileage units
            match = re.search(r'(\d+\.?\d*)\s*(km/charge|km per charge|km/kwh|km per kwh|km)', text_lower)
            if match:
                value, unit = match.groups()
                return f"{value} {unit}"
            return None

        else:
            # Petrol/Diesel
            match = re.search(r'(\d+\.?\d*)\s*(kmpl|km/l|km per liter|kilometers per liter|km)', text_lower)
            return f"{match.group(1)} kmpl" if match else None

    def query_grok(self, model_name: str, variant_name: str, fuel_type: str, year: str) -> str | None:
        """Query Grok AI for mileage information."""
        if fuel_type.lower() == "cng":
            unit_instruction = "km/kg (kilometers per kilogram) NOT kmpl"
        elif fuel_type.lower() in ["electric", "ev", "battery"]:
            unit_instruction = "km/charge or km/kWh"
        else:
            unit_instruction = "kmpl (kilometers per liter)"

        prompt = (
            f"Provide ONLY the ARAI-certified  mileage of {model_name} {variant_name} ({fuel_type}). "
            f"Use {unit_instruction}. Respond exactly like 'x km/kg' or 'x kmpl'. "
            f"Do NOT include any text, explanations, or ranges."
        )

        # Retry logic for 401 errors
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=PRIMARY_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=50,
                    temperature=0.3
                )

                if response.choices and response.choices[0].message.content:
                    content = response.choices[0].message.content.strip()
                    print(f"  Grok response: {content}")
                    return content
            except Exception as e:
                error_str = str(e)
                if "401" in error_str and attempt < max_retries - 1:
                    print(f"  ⚠️  401 error (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                else:
                    print(f"  Error querying Grok: {e}")
                    break

        return None

    def fill_missing_mileage(self, row: dict) -> str | None:
        """Fill missing mileage for a row."""
        model_name = row.get("modelName", "")
        variant_name = row.get("variantName", "")
        fuel_type = row.get("variantFuelType", row.get("variantFuel", ""))
        year = row.get("makeYear", "")

        print(f"\nProcessing: {model_name} {variant_name} ({fuel_type}, {year})")
        grok_response = self.query_grok(model_name, variant_name, fuel_type, year)
        if not grok_response:
            print("  ❌ No response from Grok")
            return None

        mileage = self.extract_mileage_value(grok_response, fuel_type)
        if not mileage:
            print("  ❌ Could not extract mileage")
            return None

        print(f"  ✓ Extracted mileage: {mileage}")
        return mileage

    def process_csv(self, input_path: str, output_path: str):
        """Process CSV file and fill missing mileage values."""
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input CSV not found: {input_path}")

        with open(input_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = reader.fieldnames

        # Determine fuel column
        fuel_column = "variantFuelType" if "variantFuelType" in fieldnames else "variantFuel"

        missing_variants = {}
        updated_count = 0

        for i, row in enumerate(rows):
            mileage = row.get("variantMileage", "").strip()
            if not mileage:
                fuel_type = row.get(fuel_column, "").strip()
                variant_key = (row.get("modelName"), row.get("variantName"), fuel_type, row.get("makeYear"))
                if variant_key not in missing_variants:
                    print(f"[Row {i+1}] Missing mileage detected")
                    new_mileage = self.fill_missing_mileage({**row, "variantFuelType": fuel_type})
                    missing_variants[variant_key] = new_mileage
                else:
                    new_mileage = missing_variants[variant_key]

                if new_mileage:
                    rows[i]["variantMileage"] = new_mileage
                    updated_count += 1

        # Write updated CSV
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"\n✅ CSV updated! Total rows updated: {updated_count}")


def main():
    print("="*60)
    print("Vehicle Variant Mileage Filler")
    print("="*60)

    if OPENROUTER_API_KEY == "<OPENROUTER_API_KEY>":
        print("⚠️  OpenRouter API key not set!")
        return

    filler = MileageFiller(OPENROUTER_API_KEY)
    filler.process_csv(INPUT_CSV_PATH, OUTPUT_CSV_PATH)


if __name__ == "__main__":
    main()
