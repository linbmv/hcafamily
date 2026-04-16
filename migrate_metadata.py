import json
import os

METADATA_FILE = "metadata.json"

def migrate():
    if not os.path.exists(METADATA_FILE):
        print("Metadata file not found.")
        return

    with open(METADATA_FILE, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    changed = False
    for item in metadata:
        local_path = item.get('local_path')
        if local_path:
            # Normalize path
            local_path = local_path.replace('\\', '/')
            item['local_path'] = local_path
            
            if not item.get('local_audio_path') and not local_path.endswith('.mp4'):
                item['local_audio_path'] = local_path
                changed = True
                print(f"Migrated audio: {item['date']} - {item['topic_zh']}")
            
            if not item.get('local_video_path') and local_path.endswith('.mp4'):
                item['local_video_path'] = local_path
                changed = True
                print(f"Migrated video: {item['date']} - {item['topic_zh']}")

    if changed:
        with open(METADATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        print("Migration complete.")
    else:
        print("No migration needed.")

if __name__ == "__main__":
    migrate()
