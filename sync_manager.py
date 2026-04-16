import threading
import traceback
from sync import run_sync as sync_hca
from sync_cscctx import run_cscctx_sync as sync_cscctx

class SyncManager:
    def __init__(self):
        self.is_syncing = False
        self.syncers = [
            ("HCA Family", sync_hca),
            ("CSCCTX Archive", sync_cscctx)
        ]

    def run_all(self):
        if self.is_syncing:
            return False
            
        self.is_syncing = True
        print("Starting master sync...")
        
        def master_task():
            try:
                for name, syncer in self.syncers:
                    print(f"--- Running {name} Sync ---")
                    try:
                        syncer()
                    except Exception as e:
                        print(f"Error in {name} syncer: {e}")
                        traceback.print_exc()
                print("Master sync complete.")
            finally:
                self.is_syncing = False

        thread = threading.Thread(target=master_task)
        thread.start()
        return True

    def get_status(self):
        return self.is_syncing

# Global instance
manager = SyncManager()
