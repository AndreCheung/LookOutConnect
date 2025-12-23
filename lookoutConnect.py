#!/usr/bin/python3

import os, sys, json, shutil, pathlib, argparse, random, requests, time, signal, fcntl
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
CAM_IP = os.getenv("CAMERA_IP", "192.168.20.25")
CAM_USER = os.getenv("CAMERA_USER", "admin")
CAM_PASS = os.getenv("CAMERA_PASS")
API_KEY = os.getenv("LOOKOUT_API_KEY")
UPLOAD_URL = f"https://lax.pop.roboticscats.com/api/detects?apiKey={API_KEY}"
SOURCE_PATH = pathlib.Path(os.getenv("SOURCE_PATH", "/home/user/ftp/files/camera2"))
FTP_ARCHIVE_DIR = pathlib.Path(os.getenv("FTP_ARCHIVE_DIR", "/home/user/ftp/files/camera2"))
BASE_DIR = pathlib.Path(__file__).parent.resolve()

LOG_FILE = FTP_ARCHIVE_DIR / "detectionResults.txt"
STATE_FILE = BASE_DIR / "last_processed.ptr"
TARGET_RES = (1920, 1080)

# --- TOOLS ---
def get_timestamp():
    """Generates a formatted string for logging and naming."""
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

def get_human_readable_size(size):
    """Convert file size into human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size) < 1024.0: return f"{size:3.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"

# --- HANDLERS ---
def timeout_handler(signum, frame):
    """Kills the process if it hangs beyond 55 seconds."""
    print(f"\n⏰ TIMEOUT at {get_timestamp()}.")
    sys.exit(1)

class ProcessLock:
    """Uses a file lock to prevent concurrent execution of the same mode."""
    def __init__(self, mode):
        self.lock_file = BASE_DIR / f"lookout_connect_{mode}.lock"
        self.fd = open(self.lock_file, 'w')

    def __enter__(self):
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except IOError:
            self.fd.close()
            sys.exit(0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()

# --- CORE FUNCTIONS ---

def log_result(filename, api_response_text):
    """Logs detections and manages 5MB log rotation."""
    try:
        data = json.loads(api_response_text)
        count = len(data.get('results', []))
        if count > 0:
            FTP_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
                LOG_FILE.replace(LOG_FILE.with_suffix('.old.txt'))
            
            log_line = f"{get_timestamp()}|{filename}|Detections: {count}|{json.dumps(data, separators=(',', ':'))}\n"
            with open(LOG_FILE, 'a') as f: f.write(log_line)
            print(f"🔥 Detection logged! ({count} found)")
            return count
    except Exception as e: print(f"⚠️ Logging error: {e}")
    return 0

def process_and_upload(file_path, is_api_mode=False, do_resize=False):
    """Uploads image, optionally resizing it first. Handles 3-attempt retry logic."""
    temp_resized = None
    final_file = file_path

    try:
        if do_resize:
            ts = get_timestamp()
            temp_resized = BASE_DIR / f"tmp_proc_{ts}.jpg"
            with Image.open(file_path) as img:
                img.thumbnail(TARGET_RES, Image.Resampling.LANCZOS)
                img.save(temp_resized, "JPEG", quality=80)
            
            # Only use resized if it actually saved space
            if temp_resized.stat().st_size < file_path.stat().st_size:
                final_file = temp_resized
            print(f"📡 Resize Enabled: Source {get_human_readable_size(file_path.stat().st_size)} -> Final {get_human_readable_size(final_file.stat().st_size)}")
        else:
            print(f"📡 Resize Disabled: Uploading original {get_human_readable_size(file_path.stat().st_size)}")

        delay = 5
        for attempt in range(1, 4):
            try:
                print(f"📡 Attempt {attempt} at {get_timestamp()}: Uploading {file_path.name}...")
                with open(final_file, 'rb') as f:
                    r = requests.post(UPLOAD_URL, data=f, headers={'Content-Type': 'image/jpeg'}, timeout=20)
                    r.raise_for_status()
                    if log_result(file_path.name, r.text) > 0 and is_api_mode:
                        FTP_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, FTP_ARCHIVE_DIR / file_path.name)
                    return True
            except Exception as e:
                print(f"⚠️ Attempt {attempt} failed: {e}")
                if attempt < 3:
                    time.sleep(delay)
                    delay *= 2
        print(f"❌ Upload failed for {file_path.name}")
    finally:
        if temp_resized and temp_resized.exists(): temp_resized.unlink()
        if is_api_mode and file_path.exists(): file_path.unlink()
    return False

# --- MODES ---

def run_api_mode(do_resize):
    """Triggers camera API snapshot and uploads."""
    ts = get_timestamp()
    print(f"🚀 Mode: API, {ts}")
    download_path = BASE_DIR / f"SNAP_{ts}.jpg"
    snap_url = f"http://{CAM_IP}/cgi-bin/api.cgi?cmd=Snap&channel=0&rs={random.randint(100,999)}&user={CAM_USER}&password={CAM_PASS}"
    try:
        with requests.get(snap_url, timeout=15, stream=True) as r:
            r.raise_for_status()
            with open(download_path, 'wb') as f: shutil.copyfileobj(r.raw, f)
        process_and_upload(download_path, is_api_mode=True, do_resize=do_resize)
    except Exception as e: print(f"⚠️ Camera Error: {e}")

def run_ftp_mode(do_resize):
    """Processes the newest image from the FTP source path."""
    print(f"📁 Mode: FTP, {get_timestamp()}")
    if not SOURCE_PATH.exists(): return
    files = [f for f in SOURCE_PATH.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')]
    if not files: return
    
    newest = max(files, key=lambda f: f.stat().st_mtime)
    file_id = f"{newest.name}|{newest.stat().st_size}|{newest.stat().st_mtime}"
    if STATE_FILE.exists() and STATE_FILE.read_text().strip() == file_id:
        print("💤 Already processed.")
        return

    if process_and_upload(newest, is_api_mode=False, do_resize=do_resize):
        STATE_FILE.write_text(file_id)
        print("✅ State updated.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["api", "ftp"])
    parser.add_argument("--resize", action="store_true", help="Enable image resizing before upload (Default: False)")
    args = parser.parse_args()

    with ProcessLock(args.mode):
        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(55)
        
        if args.mode == "api":
            run_api_mode(args.resize)
        else:
            run_ftp_mode(args.resize)
