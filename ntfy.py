#! python3
# ntfy.py | 2026-01-21 | Modular Version
# Purpose: Dispatch urgent notifications via ntfy.sh

import requests
import logging

def send_alert(image_path, topic, camera_name, detection_time, timeout=25):
    """
    Sends an urgent notification to ntfy.sh with an image attachment.
    """
    if not topic:
        logging.warning("[!] ntfy.sh topic missing. Skipping alert.")
        return False

    # ntfy uses headers to define message metadata
    headers = {
        "Title": f"LookOut Alert: {camera_name}, {detection_time}",
        "Message": "AI detection. Please check.",
        "Priority": "5",        # 5 = Urgent/Max
        "Tags": "fire,rotating_light",
        "Filename": "alert.jpg"
    }

    try:
        with open(image_path, "rb") as image_file:
            # For ntfy, the image data is sent as the request body (data=)
            response = requests.post(
                f"https://ntfy.sh/{topic}",
                data=image_file,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            logging.info("[+] ntfy.sh alert dispatched successfully.")
            return True
    except Exception as e:
        logging.error(f"[-] ntfy.sh Exception: {e}")
        return False
