#! python3
# Date: 2026015, add ntfy.sh notification

import os, pathlib, requests, logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
# Configuration for standard output logging
logging.basicConfig(filename='log.txt', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
# logging.disable(logging.ERROR)

# --- CONFIGURATION ---
CAM_NAME = os.getenv("CAMERA_NAME")
ARCHIVE_DIR = pathlib.Path(os.getenv("ARCHIVE_DIR") or "./archive")
BASE_DIR = pathlib.Path(__file__).parent.resolve()
LOG_FILE = ARCHIVE_DIR / "detectionResults.txt"
NTFY_TOPIC = os.getenv("NTFY_TOPIC")
REQUESTS_TIMER = int(os.getenv("TIMER_REQUESTS", 25))

# --- TOOLS ---
def get_timestamp(space=False):
    if space:
        return datetime.now().strftime("%Y-%m-%d %H-%M-%S") # Replaced : with - for Windows filename compatibility
    else:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# --- CORE FUNCTIONS ---
def send_ntfy_alert(image_path, camera_name, detection_time):
    if not NTFY_TOPIC:
        logging.warning("â ï¸ ntfy.sh key missing")
        return
    
    payload ={
        "title": f"LookOut alert: {camera_name}, {detection_time}",
        "message": "Please check the image.",
        "priority": "5",  # 5 = Urgent (Max priority)
        "tags": "fire,rotating_light",
        "filename": "alert.jpg"
    }

    try:
        with open(image_path, "rb") as image_file:
            requests.post(f"https://ntfy.sh/{NTFY_TOPIC}", data=image_file, headers=payload, timeout=REQUESTS_TIMER)
            logging.info("â ntfy.sh alert dispatched.")
    except Exception as e:
        logging.error(f"â ntfy.sh Exception: {e}")

"""
# Example use of send_ntfy_alert() function
if __name__ == "__main__":
    annotated_path = "testbird.jpg"
    send_ntfy_alert(annotated_path, CAM_NAME, get_timestamp('space'))
"""
