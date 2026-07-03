from flask import Flask, jsonify, request, send_from_directory
import os
import json
import threading
import time
from functools import wraps
from sync import METADATA_FILE, MEDIA_DIR, load_metadata, save_metadata
from sync_manager import manager as sync_manager
from scan_local import run_local_scan

app = Flask(__name__, static_url_path='', static_folder='.')

# --- Security Configuration ---
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'hca123')
impression_limits = {}  # { ip: [timestamp1, timestamp2, ...] }
# ------------------------------

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        password = request.headers.get('X-Admin-Password')
        if password != ADMIN_PASSWORD:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

def check_rate_limit():
    ip = request.remote_addr
    now = time.time()
    if ip not in impression_limits:
        impression_limits[ip] = []
    
    # Keep only requests from the last 60 seconds
    impression_limits[ip] = [t for t in impression_limits[ip] if now - t < 60]
    
    if len(impression_limits[ip]) >= 3:
        return False
    
    # Actually add timestamp if limit not exceeded
    impression_limits[ip].append(now)
    return True

is_syncing = False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/metadata')
def get_metadata():
    return jsonify(load_metadata())

@app.route('/api/sync', methods=['POST'])
@admin_required
def trigger_sync():
    if sync_manager.run_all():
        return jsonify({"status": "started", "message": "Master sync started in background"})
    else:
        return jsonify({"status": "busy", "message": "Sync already in progress"}), 409

@app.route('/api/scan', methods=['POST'])
@admin_required
def trigger_scan():
    result = run_local_scan()
    try:
        from clean_dups import clean_and_merge_duplicates
        clean_and_merge_duplicates()
        result["deduplicated"] = True
    except Exception as e:
        result["deduplicated_error"] = str(e)
    return jsonify(result)

@app.route('/api/status')
def get_status():
    return jsonify({"is_syncing": sync_manager.get_status()})

@app.route('/api/upload', methods=['POST'])
@admin_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
    
    subfolder = request.form.get('subfolder', '').strip()
    # Basic sanitization to prevent traversal
    subfolder = subfolder.replace('..', '').strip('/')
    
    target_dir = os.path.join(MEDIA_DIR, "misc", subfolder) if subfolder else os.path.join(MEDIA_DIR, "misc")
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    filename = file.filename
    file_path = os.path.join(target_dir, filename)
    file.save(file_path)
    
    # ROOT_DIR is defined via metadata file path in sync.py, let's ensure it's accessible or use current dir
    root_path = os.path.dirname(os.path.abspath(__file__))
    relative_path = os.path.relpath(file_path, root_path).replace('\\', '/')
    return jsonify({"status": "success", "relative_path": relative_path})

@app.route('/api/add', methods=['POST'])
@admin_required
def add_manual_entry():
    data = request.json
    required = ["date", "topic_zh", "topic_en"]
    if not all(k in data for k in required):
        return jsonify({"status": "error", "message": "Missing required fields"}), 400
    
    metadata = load_metadata()
    # Check if we should update an existing entry
    found = False
    for i, item in enumerate(metadata):
        if item['date'] == data['date'] and item['topic_zh'] == data['topic_zh']:
            metadata[i].update(data)
            found = True
            break
    
    if not found:
        metadata.append(data)
    
    save_metadata(metadata)
    return jsonify({"status": "success", "message": "Updated successfully" if found else "Added successfully"})

@app.route('/api/add_impression', methods=['POST'])
@admin_required
def add_impression():
    if not check_rate_limit():
        return jsonify({"status": "error", "message": "Too many requests"}), 429
    
    data = request.json
    date = data.get('date')
    topic_zh = data.get('topic_zh')
    text = data.get('text')
    
    if not all([date, topic_zh, text]):
        return jsonify({"status": "error", "message": "Missing fields"}), 400
    
    metadata = load_metadata()
    found = False
    for item in metadata:
        if item.get('date') == date and item.get('topic_zh') == topic_zh:
            if 'impressions' not in item or not isinstance(item['impressions'], list):
                item['impressions'] = []
            item['impressions'].append(text)
            found = True
            break
    
    if found:
        save_metadata(metadata)
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Message not found"}), 404

@app.route('/api/folders')
def get_folders():
    folder_list = []
    for root, dirs, files in os.walk(MEDIA_DIR):
        for d in dirs:
            if d.startswith('.'):
                continue
            full_path = os.path.join(root, d)
            rel_path = os.path.relpath(full_path, MEDIA_DIR).replace('\\', '/')
            folder_list.append(rel_path)
    
    # Sort: Years first (desc), then misc paths
    folder_list.sort(key=lambda x: (not x.isdigit(), x if x.isdigit() else x.lower()), reverse=False)
    # Actually, a simple sort reverse might be better for years, but let's try to be smart.
    # Years like 2026, 2025... should be at the top.
    
    years = sorted([f for f in folder_list if f.isdigit()], reverse=True)
    others = sorted([f for f in folder_list if not f.isdigit()])
    return jsonify(years + others)

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)

def start_scheduler():
    def scheduler_loop():
        # Wait 30 seconds after startup before running anything
        time.sleep(30)
        
        ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
        SCHEDULER_FILE = os.path.join(ROOT_DIR, "scheduler.json")
        
        def get_last_run_times():
            if os.path.exists(SCHEDULER_FILE):
                try:
                    with open(SCHEDULER_FILE, 'r') as sf:
                        return json.load(sf)
                except:
                    pass
            return {"last_local_scan": 0, "last_online_sync": 0}
            
        def save_last_run_times(times):
            try:
                with open(SCHEDULER_FILE, 'w') as sf:
                    json.dump(times, sf)
            except:
                pass

        while True:
            now = time.time()
            times = get_last_run_times()
            
            # 1. Run local scan & deduplicate every 12 hours (43200 seconds)
            if now - times.get("last_local_scan", 0) > 12 * 3600:
                print("[Scheduler] Running automatic local scan and deduplication...", flush=True)
                try:
                    run_local_scan()
                    from clean_dups import clean_and_merge_duplicates
                    clean_and_merge_duplicates()
                    times["last_local_scan"] = now
                    save_last_run_times(times)
                except Exception as e:
                    print(f"[Scheduler] Local scan/dedup failed: {e}", flush=True)
            
            # 2. Run online website sync every 7 days (604800 seconds)
            if now - times.get("last_online_sync", 0) > 7 * 86400:
                print("[Scheduler] Running automatic online sync...", flush=True)
                try:
                    sync_manager.run_all()
                    times["last_online_sync"] = now
                    save_last_run_times(times)
                except Exception as e:
                    print(f"[Scheduler] Online sync failed: {e}", flush=True)
                
            # Sleep for 15 minutes before checking again
            time.sleep(900)
            
    thread = threading.Thread(target=scheduler_loop, daemon=True)
    thread.start()
    print("Background scheduler thread started.", flush=True)

if __name__ == '__main__':
    # Ensure media directory
    try:
        abs_path = os.path.abspath(METADATA_FILE)
        print(f"Loading metadata from: {abs_path}", flush=True)
        if os.path.exists(METADATA_FILE):
            pass
    except:
        pass
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)
    # Ensure misc dir exists
    misc_dir = os.path.join(MEDIA_DIR, "misc")
    if not os.path.exists(misc_dir):
        os.makedirs(misc_dir)
        
    start_scheduler()
    app.run(host='0.0.0.0', port=5000)
