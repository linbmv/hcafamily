import os
import json
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://www.hcafamily.org/ui/messages/msg.php?page=wo:Phillip+Jong"
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(ROOT_DIR, "media")
METADATA_FILE = os.path.join(ROOT_DIR, "metadata.json")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
}

def setup():
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)
    if not os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)

def load_metadata():
    try:
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_metadata(metadata):
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

def extract_audio_url(onclick_text):
    match = re.search(r"playAudio\(this\s*,\s*'([^']+)'\)", onclick_text)
    return match.group(1) if match else None

def extract_video_url(onclick_text):
    match = re.search(r"playVideo\(this\s*,\s*'([^']+)'\)", onclick_text)
    return match.group(1) if match else None

def run_sync():
    setup()
    print(f"Fetching {BASE_URL}...")
    try:
        response = requests.get(BASE_URL, headers=HEADERS, timeout=30)
        if response.status_code != 200:
            return {"status": "error", "message": f"Failed to fetch page: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'class': 'table'}) or soup.find('table')
    
    if not table:
        return {"status": "error", "message": "Could not find message table."}

    rows = table.find_all('tr')[1:] # Skip header
    existing_metadata = load_metadata()
    existing_keys = { (item['date'], item['topic_zh']) for item in existing_metadata }
    
    new_items_count = 0
    downloaded_count = 0

    import time
    
    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 3: continue
            
        date = cols[0].get_text(strip=True)
        topic_cell = cols[1]
        texts = [t for t in topic_cell.stripped_strings]
        topic_en = texts[0] if len(texts) > 0 else ""
        topic_zh = texts[1] if len(texts) > 1 else ""

        # Extract URLs first so we can see if we have new info for existing records
        icons = cols[2].find_all(['span', 'i'], onclick=True)
        audio_url = None
        video_url = None
        for icon in icons:
            a = extract_audio_url(icon.get('onclick', ''))
            v = extract_video_url(icon.get('onclick', ''))
            if a: audio_url = a
            if v: video_url = v

        if (date, topic_zh) in existing_keys:
            # Smart Update: If existing entry is missing a link we just found, update it.
            item = next((x for x in existing_metadata if x['date'] == date and x['topic_zh'] == topic_zh), None)
            if item:
                updated = False
                if video_url and not item.get('video_url'):
                    item['video_url'] = video_url
                    updated = True
                if audio_url and not item.get('audio_url'):
                    item['audio_url'] = audio_url
                    updated = True
                if updated:
                    print(f"Updated missing links for {date} - {topic_zh}")
                    save_metadata(existing_metadata)
                
                # INTEGRITY CHECK: If files are missing on disk, don't skip; proceed to download section.
                # Check audio file
                audio_file_missing = item.get('local_audio_path') and not os.path.exists(os.path.join(ROOT_DIR, item['local_audio_path']))
                # Check video file (non-YouTube)
                video_file_missing = item.get('local_video_path') and not os.path.exists(os.path.join(ROOT_DIR, item['local_video_path']))
                
                if not audio_file_missing and not video_file_missing:
                    continue # Records and files are both good, skip.
                else:
                    print(f"File missing for {date} - {topic_zh}. Re-downloading...")
            else:
                continue # Safety skip
        if not audio_url and not video_url:
            continue

        new_items_count += 1
        scripture = cols[4].get_text(strip=True) if len(cols) >= 5 else ""
        meeting_type = cols[5].get_text(strip=True) if len(cols) >= 6 else ""

        item = {
            "date": date,
            "topic_en": topic_en,
            "topic_zh": topic_zh,
            "audio_url": audio_url,
            "video_url": video_url,
            "scripture": scripture,
            "type": meeting_type,
            "local_audio_path": None,
            "local_video_path": None,
            "url": audio_url or video_url # Backward compatibility
        }

        # Download Audio
        if audio_url:
            year = date.split('-')[0]
            filename = os.path.basename(audio_url)
            year_dir = os.path.join(MEDIA_DIR, year)
            if not os.path.exists(year_dir): os.makedirs(year_dir)
            local_path = os.path.join(year_dir, filename)
            
            try:
                time.sleep(0.5) # Be gentle to the server
                r = requests.get(audio_url, headers=HEADERS, stream=True, timeout=30)
                if r.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                    item['local_audio_path'] = os.path.relpath(local_path, ROOT_DIR).replace('\\', '/')
                    item['local_path'] = item['local_audio_path'] # Backward comp
                    downloaded_count += 1
            except Exception as e:
                print(f"Error downloading audio {filename}: {e}")

        # Syncing video - If it's a direct file, download. If YouTube, just keep URL.
        if video_url and not any(host in video_url for host in ['youtube.com', 'youtu.be']):
            year = date.split('-')[0]
            filename = os.path.basename(video_url)
            year_dir = os.path.join(MEDIA_DIR, year)
            if not os.path.exists(year_dir): os.makedirs(year_dir)
            local_path = os.path.join(year_dir, filename)
            
            try:
                time.sleep(0.5) # Be gentle to the server
                r = requests.get(video_url, headers=HEADERS, stream=True, timeout=30)
                if r.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): f.write(chunk)
                    item['local_video_path'] = os.path.relpath(local_path, ROOT_DIR).replace('\\', '/')
                    downloaded_count += 1
            except Exception as e:
                print(f"Error downloading video {filename}: {e}")

        existing_metadata.append(item)
        save_metadata(existing_metadata)

    return {
        "status": "success",
        "found": new_items_count,
        "downloaded": downloaded_count
    }

if __name__ == "__main__":
    result = run_sync()
    print(result)
