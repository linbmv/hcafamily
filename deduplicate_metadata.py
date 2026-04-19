import json
import os

METADATA_FILE = 'metadata.json'

def deduplicate():
    if not os.path.exists(METADATA_FILE):
        print("Metadata file not found.")
        return

    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    original_count = len(data)
    unique_data = []
    seen_keys = set()

    for item in data:
        # Use (date, topic_zh, topic_en) as unique key
        key = (item.get('date'), item.get('topic_zh', ''), item.get('topic_en', ''))
        if key not in seen_keys:
            unique_data.append(item)
            seen_keys.add(key)
    
    unique_count = len(unique_data)
    
    if original_count > unique_count:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(unique_data, f, ensure_ascii=False, indent=2)
        print(f"Successfully deduplicated. Removed {original_count - unique_count} items. Total unique: {unique_count}")
    else:
        print("No duplicates found.")

if __name__ == "__main__":
    deduplicate()
