#! python3
# LookoutConnect.py | 2026-01-21
# Purpose: Bridge IP Cameras to LookOut AI for Wildfire Detection.
# Resilience: Includes Watchdog Timer, Exponential Backoff, and Multi-cycle Logic.

import os, sys, json, shutil, pathlib, argparse, random, requests, time, signal, logging, threading
from datetime import datetime
from dotenv import load_dotenv
from requests.auth import HTTPDigestAuth
from PIL import Image, ImageDraw, ImageFont

# Support Modules.
import openWeather
import ntfy
import acsPro
import pushover

# OS-Specific File Locking to prevent race conditions
if sys.platform == "win32":
    import msvcrt
else:
    import fcntl

load_dotenv()
# Log rotation and detail level handled by logging module
logging.basicConfig(filename='log.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.DEBUG)

# --- GLOBAL CONFIGURATION ---
CAM_IP      = os.getenv("CAMERA_IP")
CAM_USER    = os.getenv("CAMERA_USER")
CAM_PASS    = os.getenv("CAMERA_PASS")
CAM_NAME    = os.getenv("CAMERA_NAME")
RAW_LOC     = os.getenv('CAMERA_LOC', '0,0')
CAM_LOC     = tuple(float(x.strip()) for x in RAW_LOC.split(','))
API_KEY     = os.getenv("LOOKOUT_API_KEY")
UPLOAD_URL  = f"https://lax.pop.roboticscats.com/api/detects?apiKey={API_KEY}"
SOURCE_PATH = pathlib.Path(os.getenv("SOURCE_PATH") or ".")
ARCHIVE_DIR = pathlib.Path(os.getenv("ARCHIVE_DIR") or "./archive")
BASE_DIR    = pathlib.Path(__file__).parent.resolve()
LOG_FILE    = ARCHIVE_DIR / "detectionResults.txt"
STATE_FILE  = BASE_DIR / "last_processed.ptr" # Tracks unique file IDs
REQUESTS_TIMER = int(os.getenv("TIMER_REQUESTS", 25))
WATCHDOG_TIMER = int(os.getenv("TIMER_WATCHDOG", 55))
TARGET_RES  = (1920, 1080)

APP_TOKEN   = os.getenv("PUSHOVER_APP_TOKEN")
USER_KEY    = os.getenv("PUSHOVER_USER_KEY")
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
ACSPro_IP = os.getenv("AXIS_IP")
ACSPro_USER = os.getenv("AXIS_USER")
ACSPro_PASS = os.getenv("AXIS_PASS")
ACSPro_RULE = os.getenv("AXIS_RULE")

# --- UTILITIES ---

def get_timestamp(space=False):
    """Generates standard timestamps. Space=True used for forensic logs."""
    fmt = "%Y-%m-%d %H-%M-%S" if space else "%Y-%m-%d_%H-%M-%S"
    return datetime.now().strftime(fmt)

def stop_script():
    """Watchdog: Forces script termination if a network request hangs indefinitely."""
    logging.error(f'TIMEOUT: Process hung for {WATCHDOG_TIMER}s. Hard exit.')
    os._exit(1)

class ProcessLock:
    """Ensures only one instance of the script (by mode) runs at a time."""
    def __init__(self, mode):
        self.lock_file = BASE_DIR / f"lookout_connect_{mode}.lock"
        self.fd = open(self.lock_file, 'w')

    def __enter__(self):
        try:
            if sys.platform == "win32":
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return self
        except (IOError, OSError):
            logging.warning("Instance already running. Skipping this execution cycle.")
            self.fd.close()
            sys.exit(0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if sys.platform == "win32":
                self.fd.seek(0)
                msvcrt.locking(self.fd.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self.fd, fcntl.LOCK_UN)
        finally:
            self.fd.close()

# --- ALERTING & LOGGING ---

def drawbbox(file_path, bbox_list, annotated_path):
    """Overlays red bounding boxes on detected smoke/fire for visual verification."""
    try:
        with Image.open(file_path) as img:
            annotated_img = img.copy()
            draw = ImageDraw.Draw(annotated_img)
            w, h = annotated_img.size
            for box in bbox_list:
                l = max(0, min(w - 1, box.get("left", 0)))
                t = max(0, min(h - 1, box.get("top", 0)))
                r = max(0, min(w - 1, box.get("right", 0)))
                b = max(0, min(h - 1, box.get("bottom", 0)))
                draw.rectangle([l, t, r, b], outline="red", width=6)
            annotated_img.save(annotated_path, "JPEG", quality=90)
    except Exception as e:
        logging.error(f"Image Annotation Error: {e}")

def log_result(file_path, api_response_text):
    """Processes AI response, writes logs, and triggers modular alerts."""
    try:
        data = json.loads(api_response_text)
        bbox_list = data.get('results', [])
        count = len(bbox_list)
        
        if count > 0:
            alert_time = get_timestamp(True)
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
            # Log Rotation at 5MB
            if LOG_FILE.exists() and LOG_FILE.stat().st_size > 5 * 1024 * 1024:
                LOG_FILE.replace(LOG_FILE.with_suffix('.old.txt'))
            
            log_line = f"{get_timestamp(True)}, {file_path.name}, Detects: {count}, {bbox_list}\n"
            with open(LOG_FILE, 'a') as f: f.write(log_line)
            logging.info(f"FIRE DETECTED: {count} findings.")

            # Prepare annotated image for alerts
            annotated_path = BASE_DIR / 'temp_annotated.jpg'
            drawbbox(file_path, bbox_list, annotated_path)

            if annotated_path and annotated_path.exists():
		        # 1. Fetch weather via module (passing Hub config down)
                weather_data = openWeather.get_current_weather(CAM_LOC, OPENWEATHER_API_KEY)
    
		        # Construct alert message
                if weather_data:
                    weather_msg = (f"\nWeather: {weather_data['description']}, "
                                   f"{weather_data['temperature_c']}C, "
                                   f"Hum: {weather_data['humidity_percent']}%")
                else:
                    weather_msg = ""

                # 2. Dispatch Pushover
                pushover.send_alert(
                    token=APP_TOKEN,
                    user=USER_KEY,
                    image_path=annotated_path,
                    title=f"LookOut Alert: {CAM_NAME}, {alert_time}",
                    message=f"AI detection. Please check.{weather_msg}",
                    cam_loc=CAM_LOC,
                )
                
                # 3. Dispatch ntfy.sh
                ntfy.send_alert(
                    image_path=annotated_path,
                    topic=NTFY_TOPIC,
                    camera_name=CAM_NAME,
                    detection_time=alert_time,
                    timeout=REQUESTS_TIMER
                )
                
                # 4. ACS Pro (Local Alarm/Siren)
                # # Passing the specific AXIS credentials defined in the Hub's .env
                acsPro.send_alert(
                    axis_ip=ACSPro_IP,
                    user=ACSPro_USER,
                    password=ACSPro_PASS,
                    rule_name=ACSPro_RULE,
                    seconds=10
                )
     
            try: annotated_path.unlink()
            except: pass
            return count
    except Exception as e:
        logging.error(f"Post-Detection Logic Error: {e}")
    return 0

# --- CORE FUNCTIONS (Log & Process) ---

def process_and_upload(file_path, is_api_mode=False, do_resize=False):
    temp_resized = None
    final_file = file_path

    try:
        if do_resize:
            temp_resized = BASE_DIR / f"TEMP_{CAM_NAME}.jpg"
            with Image.open(file_path) as img:
                img.thumbnail(TARGET_RES, Image.Resampling.LANCZOS)
                img.save(temp_resized, "JPEG", quality=80)
                logging.debug("Comparing original image and resized image file sizes.")
            if temp_resized.stat().st_size < file_path.stat().st_size:
                final_file = temp_resized
                logging.debug(f"Upload resized image, file size from {file_path.stat().st_size} to {temp_resized.stat().st_size}.")
 
        for attempt in range(1, 4):
            try:
                logging.debug(f"Attempt {attempt}: Uploading {final_file.name}...")
                with open(final_file, 'rb') as f:
                    r = requests.post(UPLOAD_URL, data=f, headers={'Content-Type': 'image/jpeg'}, timeout=REQUESTS_TIMER)
                    r.raise_for_status()

                    if log_result(final_file, r.text) > 0 and is_api_mode:
                        archive_path = BASE_DIR / f"SNAP_{get_timestamp()}.jpg"
                        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(file_path, ARCHIVE_DIR / archive_path.name)
                    return True
            except Exception as e:
                logging.warning(f"Attempt {attempt} failed: {e}")
                time.sleep(attempt * 2)
    finally:
        if temp_resized and temp_resized.exists():
            try: temp_resized.unlink()
            except: pass
        if is_api_mode and file_path.exists():
            try: file_path.unlink()
            except: pass
    return False

def run_ftp_mode(do_resize, manual_file=None):
    logging.info(f"Mode: FTP {'(Manual)' if manual_file else '(Auto)'}")
    if manual_file:
        target_file = pathlib.Path(manual_file).resolve()
        if not target_file.exists():
            logging.error(f"File not found: {manual_file}")
            return
    else:
        if not SOURCE_PATH.exists(): return
        files = [f for f in SOURCE_PATH.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg')]
        if not files: return
        target_file = max(files, key=lambda f: f.stat().st_mtime)

        # Check Pointer State    
        file_id = f"{target_file.name}|{target_file.stat().st_size}|{target_file.stat().st_mtime}"
        if STATE_FILE.exists() and STATE_FILE.read_text().strip() == file_id:
            logging.debug("Newest file already processed.") 
            return

    if process_and_upload(target_file, is_api_mode=False, do_resize=do_resize):
        if not manual_file:
            file_id = f"{target_file.name}|{target_file.stat().st_size}|{target_file.stat().st_mtime}"
            STATE_FILE.write_text(file_id)

def run_api_mode(do_resize):
    logging.info("Mode: API")
    download_path = BASE_DIR / f"SNAP_{CAM_NAME}.jpg"
    # AXIS API
    snap_url = f"http://{CAM_IP}/axis-cgi/jpg/image.cgi?resolution=1920x1080"
    # Reolink API
    # snap_url = f"http://{CAM_IP}/cgi-bin/api.cgi?cmd=Snap&channel=0&rs={random.randint(100,999)}&user={CAM_USER}&password={CAM_PASS}"
    try:
        # Call Axis API
        r = requests.get(snap_url, verify=False, auth=HTTPDigestAuth(CAM_USER, CAM_PASS), timeout=REQUESTS_TIMER)
        # Call Reolink API
        # r = requests.get(snap_url, timeout=REQUESTS_TIMER)
        
        r.raise_for_status()
        with open(download_path, 'wb') as f: f.write(r.content)
        process_and_upload(download_path, is_api_mode=True, do_resize=do_resize)
    except Exception as e:
        logging.error(f"Camera API Error: {e}")


# --- MAIN EXECUTION LOOP ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LookoutConnect Wildfire Sentinel")
    parser.add_argument("mode", choices=["api", "ftp"], help="Capture mode")
    parser.add_argument("--resize", action="store_true", help="Downscale to 1080p")
    parser.add_argument("--file", type=str, help="Manual file upload override")
    parser.add_argument("--runs", type=int, default=1, help="Number of 60s duty cycles")
    args = parser.parse_args()

    # Apply process lock for the entire session duration
    with ProcessLock(args.mode):
        for cycle in range(1, args.runs + 1):
            cycle_start = time.time()
            
            # Initialize Watchdog for this specific 60s window
            watchdog = threading.Timer(WATCHDOG_TIMER, stop_script)
            watchdog.daemon = True
            watchdog.start()

            try:
                if args.mode == "api":
                    run_api_mode(args.resize)
                else:
                    run_ftp_mode(args.resize, manual_file=args.file)
            except Exception as e:
                logging.error(f"Cycle {cycle} execution failure: {e}")
            finally:
                watchdog.cancel() # Clear watchdog if task finished safely

            # Maintenance of 60-second intervals for multi-run scheduling
            if cycle < args.runs:
                elapsed = time.time() - cycle_start
                wait = max(0, 60 - elapsed)
                if wait > 0:
                    time.sleep(wait)

    logging.info("All scheduled runs completed. System standby.")
