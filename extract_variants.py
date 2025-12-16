import csv
import os

from scrapy.selector import Selector

# Define output directory structure
output_dir = "Output/Mahindra/xuv700"
os.makedirs(output_dir, exist_ok=True)

# Read the HTML file
with open("txt.txt", "r", encoding="utf-8") as f:
    html_content = f.read()

# Parse HTML with Scrapy Selector
selector = Selector(text=html_content)

# Find all feature/spec sections
sections = selector.xpath('//div[contains(@class, "_1egt6kt9")]')

# Dictionary to store features and specifications
features_data = {}
specs_data = {}

# Process each section
for section in sections:
    section_id = section.xpath("@id").get()

    # Find all variant columns in this section
    variants = section.xpath('.//div[contains(@class, "_1egt6kth")]')

    for variant_idx, variant in enumerate(variants, 1):
        # Get the feature/spec name
        title = variant.xpath('.//div[contains(@class, "_1ivmml5uy")]/text()').get()
        if not title:
            continue

        feature_name = title.strip()

        # Get all the specifications under this feature
        # Find all p tags with specifications
        specs = variant.xpath('.//div[contains(@class, "_1ivmml5ur")]//p')

        for spec in specs:
            spans = spec.xpath(".//span/text()").getall()
            if len(spans) >= 2:
                spec_name = spans[0].strip()
                spec_value = spans[1].strip()

                # Remove the feature name prefix from spec name if it exists
                if spec_name.startswith(feature_name):
                    spec_name = spec_name[len(feature_name) :].strip()

                # Create unique key for this spec
                full_spec_name = (
                    f"{feature_name} - {spec_name}" if spec_name else feature_name
                )

                # Determine if this is a feature or specification
                # Features are boolean-like (yes/no) or single values
                # Specifications are more detailed measurements
                if spec_value.lower() in ["yes", "no"] or not spec_name:
                    # This is a feature
                    if full_spec_name not in features_data:
                        features_data[full_spec_name] = {}
                    features_data[full_spec_name][f"Variant {variant_idx}"] = spec_value
                else:
                    # This is a specification
                    if full_spec_name not in specs_data:
                        specs_data[full_spec_name] = {}
                    specs_data[full_spec_name][f"Variant {variant_idx}"] = spec_value

# Get the maximum number of variants
max_variants = 0
if features_data:
    for feat in features_data:
        if features_data[feat]:
            variant_nums = [int(k.split()[1]) for k in features_data[feat].keys()]
            if variant_nums:
                max_variants = max(max_variants, max(variant_nums))

if specs_data:
    for spec in specs_data:
        if specs_data[spec]:
            variant_nums = [int(k.split()[1]) for k in specs_data[spec].keys()]
            if variant_nums:
                max_variants = max(max_variants, max(variant_nums))

# Create features CSV
if features_data:
    features_path = os.path.join(output_dir, "Features.csv")
    with open(features_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        header = ["Feature"] + [f"Subvariant {i}" for i in range(1, max_variants + 1)]
        writer.writerow(header)

        # Write data
        for feature_name in sorted(features_data.keys()):
            row = [feature_name]
            for i in range(1, max_variants + 1):
                variant_key = f"Variant {i}"
                row.append(features_data[feature_name].get(variant_key, ""))
            writer.writerow(row)

    print(
        f"Features CSV created at {features_path} with {len(features_data)} features and {max_variants} variants"
    )
else:
    print("No features found")

# Create specifications CSV
if specs_data:
    specs_path = os.path.join(output_dir, "Specifications.csv")
    with open(specs_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Write header
        header = ["Specification"] + [
            f"Subvariant {i}" for i in range(1, max_variants + 1)
        ]
        writer.writerow(header)

        # Write data
        for spec_name in sorted(specs_data.keys()):
            row = [spec_name]
            for i in range(1, max_variants + 1):
                variant_key = f"Variant {i}"
                row.append(specs_data[spec_name].get(variant_key, ""))
            writer.writerow(row)

    print(
        f"Specifications CSV created at {specs_path} with {len(specs_data)} specifications and {max_variants} variants"
    )
else:
    print("No specifications found")
