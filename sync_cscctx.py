import requests
from bs4 import BeautifulSoup
import os
import json
import re
import time
from datetime import datetime

# Configuration
BASE_URL = "https://cscctx.org/"
ARCHIVE_URL = "https://cscctx.org/sermonaudio.htm"
METADATA_FILE = "metadata.json"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MISC_DIR = os.path.join(ROOT_DIR, "media", "misc", "cscctx")
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_metadata(data):
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def run_cscctx_sync():
    print(f"Starting CSCCTX Sync from {ARCHIVE_URL}...")
    metadata = load_metadata()
    existing_keys = {(m['date'], m['topic_zh']) for m in metadata}
    
    response = requests.get(ARCHIVE_URL, headers=HEADERS)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all yearly sermon links (e.g., 2026sermons.html)
    year_links = []
    for a in soup.find_all('a', href=True):
        if 'sermons.html' in a['href']:
            url = a['href'] if a['href'].startswith('http') else BASE_URL + a['href']
            if url not in year_links:
                year_links.append(url)
    
    print(f"Found {len(year_links)} yearly archives.")
    
    new_items_count = 0
    
    for year_url in year_links:
        print(f"Scanning archive: {year_url}")
        try:
            r = requests.get(year_url, headers=HEADERS)
            r.encoding = 'utf-8' # Ensure Chinese is parsed correctly
            s = BeautifulSoup(r.text, 'html.parser')
            
            # The format is often <a> tags with the info as text
            links = s.find_all('a', href=True)
            for link in links:
                text = link.get_text(strip=True)
                # Filter for Phillip Jong (钟理恩)
                if "钟理恩" in text or "Phillip Jong" in text:
                    # Parse: Preacher - Topic Date
                    # Example: [钟理恩 - 火焰和荊棘 02-08-2026]
                    match = re.search(r'(.*?)\s*-\s*(.*?)\s+(\d{2}-\d{2}-\d{4})', text)
                    if not match: continue
                    
                    preacher = match.group(1).strip()
                    topic = match.group(2).strip()
                    date_str = match.group(3).strip()
                    
                    # Convert date to YYYY-MM-DD
                    try:
                        dt = datetime.strptime(date_str, '%m-%d-%Y')
                        date = dt.strftime('%Y-%m-%d')
                    except:
                        continue
                        
                    if (date, topic) in existing_keys:
                        continue
                    
                    audio_url = link['href']
                    if not audio_url.startswith('http'):
                        audio_url = BASE_URL + audio_url
                    
                    # Download
                    year = date.split('-')[0]
                    filename = os.path.basename(audio_url)
                    target_dir = os.path.join(MISC_DIR, year)
                    if not os.path.exists(target_dir): os.makedirs(target_dir)
                    
                    local_path = os.path.join(target_dir, filename)
                    
                    if not os.path.exists(local_path):
                        print(f"Downloading: {date} - {topic}")
                        try:
                            time.sleep(0.5)
                            audio_r = requests.get(audio_url, headers=HEADERS, stream=True, timeout=30)
                            if audio_r.status_code == 200:
                                with open(local_path, 'wb') as f:
                                    for chunk in audio_r.iter_content(chunk_size=8192):
                                        f.write(chunk)
                            else:
                                print(f"Failed to download audio: {audio_url}")
                                continue
                        except Exception as e:
                            print(f"Download error: {e}")
                            continue
                    
                    # Successfully got it
                    rel_path = os.path.relpath(local_path, ROOT_DIR).replace('\\', '/')
                    new_item = {
                        "date": date,
                        "topic_zh": topic,
                        "topic_en": "",
                        "url": audio_url,
                        "audio_url": audio_url,
                        "video_url": None,
                        "local_audio_path": rel_path,
                        "scripture": "CSCCTX Archive",
                        "type": "CSCCTX Sermon"
                    }
                    metadata.append(new_item)
                    existing_keys.add((date, topic))
                    new_items_count += 1
                    
                    # Save every item to be safe
                    save_metadata(metadata)
                    
        except Exception as e:
            print(f"Error scanning {year_url}: {e}")
            
    print(f"CSCCTX Sync complete. Added {new_items_count} new entries.")

if __name__ == "__main__":
    run_cscctx_sync()
