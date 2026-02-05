import json
import re

# Read the JSON file
with open('temp_import_901_910.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Add page field to each record
for record in data:
    # Extract page number from image_id (e.g., "page_0901_img_01_clip.jpg" -> 901)
    image_id = record.get('image_id', '')
    match = re.search(r'page_(\d+)_', image_id)
    if match:
        page_num = int(match.group(1))
        # Insert page field after image_id
        record['page'] = page_num

# Write corrected JSON back
with open('temp_import_901_910_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Fixed {len(data)} records")
print("Created: temp_import_901_910_fixed.json")
