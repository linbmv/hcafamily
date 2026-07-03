import os
import json
import re
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(ROOT_DIR, "media")
METADATA_FILE = os.path.join(ROOT_DIR, "metadata.json")

AUDIO_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.wma', '.aac', '.flac', '.opus', '.ogg')
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.wmv', '.webm', '.flv')

def load_metadata():
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading metadata: {e}")
    return []

def save_metadata(metadata):
    try:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print("Metadata saved successfully.")
    except Exception as e:
        print(f"Error saving metadata: {e}")

def parse_filename(filename):
    """
    Parse filename to extract date, Chinese topic, English topic, and type.
    Example: '20260322_1213PhillipJong.mp3' -> Date: 2026-03-22
    Example: '2026-05-18_We are His workmanship_我们是他手中的工作.mp3'
    """
    # Strip extension
    base, ext = os.path.splitext(filename)
    
    # 1. Look for YYYY-MM-DD
    date_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', base)
    if date_match:
        date_str = date_match.group(0)
        base = base.replace(date_str, '')
    else:
        # Look for YYYYMMDD
        date_match = re.search(r'(\d{4})(\d{2})(\d{2})', base)
        if date_match:
            try:
                dt = datetime.strptime(date_match.group(0), '%Y%m%d')
                date_str = dt.strftime('%Y-%m-%d')
                base = base.replace(date_match.group(0), '')
            except ValueError:
                date_str = None
        else:
            date_str = None

    # Clean up name remnants like preacher, underscores, dashes, spaces
    clean_base = base
    # Remove preacher names
    for name in ['PhillipJong', 'Phillip Jong', 'Phillip_Jong', '钟理恩', 'sermon', 'sharing']:
        clean_base = re.sub(re.escape(name), '', clean_base, flags=re.IGNORECASE)
    
    # Replace dashes and underscores with spaces, then split/strip
    clean_base = clean_base.replace('_', ' - ').replace('  ', ' ').strip(' -_ ')
    
    # Split Chinese and English
    parts = [p.strip() for p in clean_base.split(' - ') if p.strip()]
    
    topic_zh = ""
    topic_en = ""
    
    # Helper to detect Chinese characters
    def has_chinese(s):
        return bool(re.search(r'[\u4e00-\u9fff]', s))

    for part in parts:
        if has_chinese(part):
            topic_zh = part
        else:
            topic_en = part
            
    # Try meeting type detection
    meeting_type = "Sermon"
    if "friday" in filename.lower():
        meeting_type = "Friday Sharing"
    elif "sunday" in filename.lower():
        meeting_type = "Sunday Sharing"
        
    return date_str, topic_zh, topic_en, meeting_type

def run_local_scan():
    if not os.path.exists(MEDIA_DIR):
        print(f"Media directory {MEDIA_DIR} does not exist.")
        return {"status": "error", "message": "Media directory not found"}

    metadata = load_metadata()
    
    # Map of existing files in metadata to avoid duplicate records
    existing_files = set()
    for item in metadata:
        for path_key in ['local_audio_path', 'local_video_path', 'local_path']:
            path = item.get(path_key)
            if path:
                existing_files.add(path.replace('\\', '/').strip('/'))

    new_files_count = 0
    matched_files_count = 0
    
    # Walk the media directory
    for root, dirs, files in os.walk(MEDIA_DIR):
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in AUDIO_EXTENSIONS and ext not in VIDEO_EXTENSIONS:
                continue
                
            full_path = os.path.join(root, file)
            # Make path relative to ROOT_DIR
            rel_path = os.path.relpath(full_path, ROOT_DIR).replace('\\', '/').strip('/')
            
            if rel_path in existing_files:
                continue
            
            # Found a file not registered in metadata!
            is_audio = ext in AUDIO_EXTENSIONS
            print(f"Found unregistered media file: {rel_path}")
            
            # Parse info from filename
            date_str, topic_zh, topic_en, meeting_type = parse_filename(file)
            
            # If no date could be parsed, default to current date or file creation date
            if not date_str:
                # Try to get date from directory name if it's a 4 digit year
                dir_name = os.path.basename(root)
                if re.match(r'^\d{4}$', dir_name):
                    date_str = f"{dir_name}-01-01"  # fallback
                else:
                    stat = os.stat(full_path)
                    dt = datetime.fromtimestamp(stat.st_mtime)
                    date_str = dt.strftime('%Y-%m-%d')
            
            # Check if we can smart-match this with an existing entry on the same date
            matched = False
            for item in metadata:
                if item.get('date') == date_str:
                    # Check if the title is similar or if there's no title, or if we just match by date and missing path
                    if is_audio and not item.get('local_audio_path'):
                        item['local_audio_path'] = rel_path
                        # Also sync local_path if not set
                        if not item.get('local_path'):
                            item['local_path'] = rel_path
                        matched = True
                        matched_files_count += 1
                        print(f"Smart-matched {file} as audio for existing date {date_str}")
                        break
                    elif not is_audio and not item.get('local_video_path'):
                        item['local_video_path'] = rel_path
                        matched = True
                        matched_files_count += 1
                        print(f"Smart-matched {file} as video for existing date {date_str}")
                        break
            
            if not matched:
                # Create a new entry
                new_item = {
                    "date": date_str,
                    "topic_zh": topic_zh or file,
                    "topic_en": topic_en,
                    "url": None,
                    "audio_url": None,
                    "video_url": None,
                    "local_audio_path": rel_path if is_audio else None,
                    "local_video_path": rel_path if not is_audio else None,
                    "local_path": rel_path,
                    "scripture": "Local Scan",
                    "type": meeting_type
                }
                metadata.append(new_item)
                new_files_count += 1
                print(f"Created new metadata entry for: {file} ({date_str})")
                
            # Add to set so we don't double process
            existing_files.add(rel_path)

    if new_files_count > 0 or matched_files_count > 0:
        # Sort metadata by date descending
        try:
            metadata.sort(key=lambda x: x.get('date', ''), reverse=True)
        except Exception as e:
            print(f"Error sorting metadata: {e}")
            
        save_metadata(metadata)
        
    return {
        "status": "success",
        "new_entries": new_files_count,
        "matched_entries": matched_files_count
    }

if __name__ == "__main__":
    result = run_local_scan()
    print(result)
