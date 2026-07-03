import os
import json
import hashlib
from collections import defaultdict

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_FILE = os.path.join(ROOT_DIR, "metadata.json")

def get_file_hash(filepath):
    """Calculate MD5 hash of a file to check for exact identity."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Error hashing {filepath}: {e}")
        return None

def clean_and_merge_duplicates():
    if not os.path.exists(METADATA_FILE):
        print("metadata.json not found.")
        return
        
    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
        
    print(f"Total entries before cleanup: {len(metadata)}")
    
    # Group items by date to analyze potential duplicates
    by_date = defaultdict(list)
    for item in metadata:
        by_date[item.get('date')].append(item)
        
    cleaned_metadata = []
    removed_records_count = 0
    deleted_files_count = 0
    
    for date, items in by_date.items():
        if len(items) == 1:
            cleaned_metadata.append(items[0])
            continue
            
        # If there are multiple items on the same date, check if they are the same meeting
        # or different meetings (e.g. Sunday Sharing vs. Sunday School)
        unique_groups = [] # List of merged item dictionaries for this date
        
        for item in items:
            matched_group = None
            item_topic_zh = item.get('topic_zh', '').strip().lower()
            item_topic_en = item.get('topic_en', '').strip().lower()
            item_type = item.get('type', '').strip().lower()
            
            for group in unique_groups:
                g_topic_zh = group.get('topic_zh', '').strip().lower()
                g_topic_en = group.get('topic_en', '').strip().lower()
                g_type = group.get('type', '').strip().lower()
                
                # Check if topics are identical/empty or very similar, and types match
                # (Or if it's the exact same sermon but one has empty title)
                same_topic = (item_topic_zh == g_topic_zh and item_topic_zh != '') or \
                             (item_topic_en == g_topic_en and item_topic_en != '') or \
                             (item_topic_zh == '' and g_topic_zh != '') or \
                             (g_topic_zh == '' and item_topic_zh != '')
                             
                same_type = (item_type == g_type) or (item_type in ['', 'sermon'] or g_type in ['', 'sermon'])
                
                if same_topic and same_type:
                    matched_group = group
                    break
            
            if matched_group:
                # Prioritize keeping online scraper metadata!
                # If matched_group is a 'Local Scan' entry, but the current item is an online scraped entry,
                # swap them so that we keep the rich online metadata in the matched_group.
                is_g_local = (matched_group.get('scripture') == 'Local Scan')
                is_i_local = (item.get('scripture') == 'Local Scan')
                
                if is_g_local and not is_i_local:
                    temp = matched_group.copy()
                    matched_group.clear()
                    matched_group.update(item)
                    item = temp
                    
                # Merge fields!
                print(f"\n[Merge] Duplicate record found on {date}:")
                print(f"  Keep:   {matched_group.get('topic_zh')} ({matched_group.get('type')})")
                print(f"  Merge:  {item.get('topic_zh')} ({item.get('type')})")
                
                # Fill missing titles/info
                if not matched_group.get('topic_zh') and item.get('topic_zh'):
                    matched_group['topic_zh'] = item['topic_zh']
                if not matched_group.get('topic_en') and item.get('topic_en'):
                    matched_group['topic_en'] = item['topic_en']
                if matched_group.get('type') in ['', 'sermon'] and item.get('type') not in ['', 'sermon']:
                    matched_group['type'] = item['type']
                if not matched_group.get('scripture') and item.get('scripture'):
                    matched_group['scripture'] = item['scripture']
                if not matched_group.get('tags') and item.get('tags'):
                    matched_group['tags'] = item['tags']
                elif matched_group.get('tags') and item.get('tags'):
                    # Merge unique tags
                    t1 = [t.strip() for t in matched_group['tags'].split(',') if t.strip()]
                    t2 = [t.strip() for t in item['tags'].split(',') if t.strip()]
                    matched_group['tags'] = ", ".join(sorted(list(set(t1 + t2))))
                    
                # Merge impressions comments
                if 'impressions' in item:
                    if 'impressions' not in matched_group:
                        matched_group['impressions'] = []
                    for imp in item['impressions']:
                        if imp not in matched_group['impressions']:
                            matched_group['impressions'].append(imp)
                
                # Deduplicate audio and video paths
                for path_key in ['local_audio_path', 'local_video_path', 'local_path']:
                    g_path = matched_group.get(path_key)
                    i_path = item.get(path_key)
                    
                    if i_path and g_path and i_path != g_path:
                        # We have two different file paths referenced!
                        # Check if they are physically duplicate files
                        full_g_path = os.path.join(ROOT_DIR, g_path)
                        full_i_path = os.path.join(ROOT_DIR, i_path)
                        
                        hash_g = get_file_hash(full_g_path)
                        hash_i = get_file_hash(full_i_path)
                        
                        if hash_g and hash_i and hash_g == hash_i:
                            # Files are identical! Delete the duplicate file
                            try:
                                os.remove(full_i_path)
                                deleted_files_count += 1
                                print(f"  Deleted duplicate physical file: {i_path}")
                            except Exception as e:
                                print(f"  Failed to delete file {i_path}: {e}")
                        else:
                            # Not identical or one is missing. We keep the matched group path,
                            # but let's notify the user.
                            print(f"  Warning: Different physical files detected for same sermon: {g_path} vs {i_path}. Keeping {g_path}.")
                    elif i_path and not g_path:
                        # Pull path to the group if missing
                        matched_group[path_key] = i_path
                
                removed_records_count += 1
            else:
                # Add as a unique meeting on this day (e.g. Sunday School vs Sunday Sharing)
                unique_groups.append(item)
                
        cleaned_metadata.extend(unique_groups)
        
    if removed_records_count > 0:
        # Sort metadata
        cleaned_metadata.sort(key=lambda x: x.get('date', ''), reverse=True)
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(cleaned_metadata, f, ensure_ascii=False, indent=2)
        print(f"\nDeduplication complete.")
        print(f"  - Removed duplicate records: {removed_records_count}")
        print(f"  - Deleted duplicate files: {deleted_files_count}")
        print(f"  - Remaining records: {len(cleaned_metadata)}")
    else:
        print("\nNo duplicates found to merge.")

if __name__ == "__main__":
    clean_and_merge_duplicates()
