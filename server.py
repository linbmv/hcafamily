from flask import Flask, jsonify, request, send_from_directory
import os
import json
import threading
from sync import run_sync, METADATA_FILE, MEDIA_DIR, load_metadata, save_metadata

app = Flask(__name__, static_url_path='', static_folder='.')

is_syncing = False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/metadata')
def get_metadata():
    return jsonify(load_metadata())

@app.route('/api/sync', methods=['POST'])
def trigger_sync():
    global is_syncing
    if is_syncing:
        return jsonify({"status": "busy", "message": "Sync already in progress"}), 409
    
    def sync_task():
        global is_syncing
        is_syncing = True
        try:
            run_sync()
        finally:
            is_syncing = False

    thread = threading.Thread(target=sync_task)
    thread.start()
    return jsonify({"status": "started", "message": "Sync started in background"})

@app.route('/api/status')
def get_status():
    return jsonify({"is_syncing": is_syncing})

@app.route('/api/upload', methods=['POST'])
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

@app.route('/media/<path:filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_DIR, filename)

if __name__ == '__main__':
    # Ensure media directory exists
    if not os.path.exists(MEDIA_DIR):
        os.makedirs(MEDIA_DIR)
    # Ensure misc dir exists
    misc_dir = os.path.join(MEDIA_DIR, "misc")
    if not os.path.exists(misc_dir):
        os.makedirs(misc_dir)
    app.run(host='0.0.0.0', port=5000)
