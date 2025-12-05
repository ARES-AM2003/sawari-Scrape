import pandas as pd
import glob
import os
import random

csv_folder = "/home/ares-am/Projects/BNT/scrapy/Output/Maruti/Ciaz"

sheet_name = os.path.basename(csv_folder.rstrip("/"))
# Create 'combined' folder in the same directory as CSV files
combined_folder = os.path.join(csv_folder, "combined")
os.makedirs(combined_folder, exist_ok=True)
output_file = os.path.join(combined_folder, f"{sheet_name}-sheet.xlsx")
# Output file will be saved in the 'combined' folder
# output_file = os.path.join(combined_folder, "kona-sheet.xlsx")

csv_files = glob.glob(os.path.join(csv_folder, "*.csv"))

# Define Categories sheet data
categories_data = {
    'featureCategory': [
        'Exterior',
        'Safety',
        'Comfort & Convenience',
        'Lighting',
        'Braking & Traction',
        'Locks & Security',
        'Doors, Windows, Mirrors & Wipers',
        'Entertainment, Information & Communication',
        'Seats & Upholstery',
        'Mobile App Features',
        'Instrumentation',
        'Storage',
        'Off Road Essentials',
        'Manufacturer Warranty'
    ],
    'specificationCategory': [
        'Engine & Transmission',
        'Dimensions & Weight',
        'Capacity',
        'Suspensions, Brakes, Steering & Tyres',
        'Electric Motor & Battery',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'ratingCategory': [
        'Exterior Design And Engineering',
        'Interior Space And Comfort',
        'Performance And Refinement',
        'Mileage / Range And Efficiency',
        'Ride Comfort And Handling',
        'Features And Safety',
        'Value For Money',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ],
    'bodyType': [
        'Sedan',
        'Pick-Up',
        'Hatchback',
        'MUV',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        '',
        ''
    ]
}

# Extract model from csv_folder path
path_parts = csv_folder.strip('/').split('/')
model_name = path_parts[-1].capitalize()  # altroz -> Altroz

# Define ModelYears sheet data
model_years_data = {
    'modelName': [model_name],
    'makeYear': [2025],
    'makeYearIsPopular': [random.choice([True, False])]
}

with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
    # Create Categories sheet first
    categories_df = pd.DataFrame(categories_data)
    categories_df.to_excel(writer, sheet_name='Categories', index=False)

    # Create ModelYears sheet
    model_years_df = pd.DataFrame(model_years_data)
    model_years_df.to_excel(writer, sheet_name='ModelYears', index=False)

    # Add CSV files as separate sheets
    for csv_file in csv_files:
        # Use the file name (without extension) as sheet name
        sheet_name = os.path.splitext(os.path.basename(csv_file))[0]

        # Check if this is the Features sheet - it has no headers
        if sheet_name == 'Features':
            df = pd.read_csv(csv_file, on_bad_lines='skip', header=None,
                           names=['modelName', 'makeYear', 'variantName', 'featureCategoryName', 'featureName', 'featureValue','featureIsHighlighted'])
        else:
            # Read CSV, skip bad lines
            df = pd.read_csv(csv_file, on_bad_lines='skip')

        # Write to Excel sheet
        df.to_excel(writer, sheet_name=sheet_name, index=False)

print(f"All CSV files have been merged into {output_file}")
print(f"Categories sheet added with default data")
print(f"ModelYears sheet added with columns: modelName, makeYear, makeYearIsPopular")
