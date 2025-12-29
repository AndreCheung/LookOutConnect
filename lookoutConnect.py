#! /usr/bin/python3
# lookoutConnectV4.py | 20251229 | Pushover Alerts & Manual File Upload
import os, sys, json, shutil, pathlib, argparse, random, requests, time, signal, fcntl, logging
from datetime import datetime
from PIL import Image
from dotenv import load_dotenv

load_dotenv()
# Configuration for standard output logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION ---
CAM_IP = os.getenv("CAMERA_IP")
CAM_USER = os.getenv("CAMERA_USER")
CAM_PASS = os.getenv("CAMERA_PASS")
CAM_NAME = os.getenv("CAMERA_NAME")
API_KEY = os.getenv("LOOKOUT_API_KEY")
UPLOAD_URL = f"https://lax.pop.roboticscats.com/api/detects?apiKey={API_KEY}"
SOURCE_PATH = pathlib.Path(os.getenv("SOURCE_PATH"))
ARCHIVE_DIR = pathlib.Path(os.getenv("ARCHIVE_DIR"))
BASE_DIR = pathlib.Path(__file__).parent.resolve()
LOG_FILE = ARCHIVE_DIR / "detectionResults.txt"
STATE_FILE = BASE_DIR / "last_processed.ptr"
APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN")
USER_KEY = os.getenv("PUSHOVER_USER_KEY")
WATCHDOG_TIMER = int(os.getenv("TIMER_THRESHOLD", 55))
TARGET_RES = (1920, 1080)

# --- TOOLS ---
def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

def get_human_readable_size(size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(size) < 1024.0: return f"{size:3.1f}{unit}"
        size /= 1024.0
    return f"{size:.1f}TB"

# --- HANDLERS ---
def timeout_handler(signum, frame):
    logging.error('â° TIMEOUT: Script exceeded 55s limit.')
    sys.exit(1)

class ProcessLock:
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

# --- ALERTING ---

def send_pushover_alert(image_path, camera_name, detection_time):
    """Sends emergency alert via Pushover API."""
    if not APP_TOKEN or not USER_KEY:
        logging.warning("â ï¸ Pushover keys missing in .env")
        return

    payload = {
        "token": APP_TOKEN,
        "user": USER_KEY,
        "title": f"ð¥ LookOut alert: {camera_name}, {detection_time}",
        "message": f"Please check the image.",
        "priority": 2,      # Emergency priority
        "retry": 60,        # Acknowledge requirement
        "expire": 3600,
        "sound": "persistent" 
    }

    try:
        with open(image_path, "rb") as image_file:
            files = {"attachment": ("alert.jpg", image_file, "image/jpeg")}
            response = requests.post("https://api.pushover.net/1/messages.json", data=payload, files=files, timeout=15)
        
        if response.status_code == 200:
            logging.info("â Pushover alert dispatched.")
        else:
            logging.error(f"â Pushover failed: {response.text}")
    except Exception as e:
        logging.error(f"â Pushover Exception: {e}")

# --- CORE FUNCTIONS ---

def log_result(filename, api_response_text, original_path):
    """Logs detections, manages log rotation, and triggers alerts."""
    try:
        data = json.loads(api_response_text)
        count = len(data.get('results', []))
        if count > 0:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            # Log Rotation
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
                LOG_FILE.replace(LOG_FILE.with_suffix('.old.txt'))
            
            log_line = f"{get_timestamp()}|{filename}|Detections: {count}|{json.dumps(data, separators=(',', ':'))}\n"
            with open(LOG_FILE, 'a') as f: f.write(log_line)

            # Alerting
            send_pushover_alert(original_path, CAM_NAME, get_timestamp())
            logging.info(f"ð¥ OBJECT DETECTED: {count} results found.")
            return count
    except Exception as e:
        logging.error(f"â ï¸ Logging error: {e}")
    return 0

def process_and_upload(file_path, is_api_mode=False, do_resize=False):
    temp_resized = None
    final_file = file_path

    try:
        if do_resize:
            temp_resized = BASE_DIR / f"tmp_proc_{get_timestamp()}.jpg"
            with Image.open(file_path) as img:
                img.thumbnail(TARGET_RES, Image.Resampling.LANCZOS)
                img.save(temp_resized, "JPEG", quality=80)
            if temp_resized.stat().st_size < file_path.stat().st_size:
                final_file = temp_resized
        
        for attempt in range(1, 4):
            try:
                logging.debug(f"ð¡ Attempt {attempt}: Uploading {file_path.name}...")
                with open(final_file, 'rb') as f:
                    r = requests.post(UPLOAD_URL, data=f, headers={'Content-Type': 'image/jpeg'}, timeout=20)
                    r.raise_for_status()
                    
                    if log_result(file_path.name, r.text, file_path) > 0 and is_api_mode:
                        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, ARCHIVE_DIR / file_path.name)
                    return True
            except Exception as e:
                logging.warning(f"â ï¸ Attempt {attempt} failed: {e}")
                if attempt < 3: time.sleep(attempt * 5)
    finally:
        if temp_resized and temp_resized.exists(): temp_resized.unlink()
        if is_api_mode and file_path.exists(): file_path.unlink()
    return False

# --- MODES ---

def run_ftp_mode(do_resize, manual_file=None):
    logging.info(f"ð Mode: FTP {'(Manual)' if manual_file else '(Auto)'}")
    
    if manual_file:
        target_file = pathlib.Path(manual_file).resolve()
        if not target_file.exists():
            logging.error(f"â File not found: {manual_file}")
            return
    else:
        if not SOURCE_PATH.exists(): return
        files = [f for f in SOURCE_PATH.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')]
        if not files: return
        target_file = max(files, key=lambda f: f.stat().st_mtime)

        # Check Pointer State
        file_id = f"{target_file.name}|{target_file.stat().st_size}|{target_file.stat().st_mtime}"
        if STATE_FILE.exists() and STATE_FILE.read_text().strip() == file_id:
            logging.debug("ð¤ Newest file already processed.")
            return

    if process_and_upload(target_file, is_api_mode=False, do_resize=do_resize):
        if not manual_file:
            file_id = f"{target_file.name}|{target_file.stat().st_size}|{target_file.stat().st_mtime}"
            STATE_FILE.write_text(file_id)

def run_api_mode(do_resize):
    logging.info("ð€ Mode: API")
    download_path = BASE_DIR / f"SNAP_{get_timestamp()}.jpg"
    snap_url = f"http://{CAM_IP}/cgi-bin/api.cgi?cmd=Snap&channel=0&rs={random.randint(100,999)}&user={CAM_USER}&password={CAM_PASS}"
    try:
        r = requests.get(snap_url, timeout=15)
        r.raise_for_status()
        with open(download_path, 'wb') as f: f.write(r.content)
        process_and_upload(download_path, is_api_mode=True, do_resize=do_resize)
    except Exception as e:
        logging.error(f"â ï¸ Camera API Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["api", "ftp"])
    parser.add_argument("--resize", action="store_true")
    parser.add_argument("--file", type=str)
    args = parser.parse_args()

    with ProcessLock(args.mode):
        if sys.platform != "win32":
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(WATCHDOG_TIMER)
        
        if args.mode == "api":
            run_api_mode(args.resize)
        else:
            run_ftp_mode(args.resize, manual_file=args.file)
