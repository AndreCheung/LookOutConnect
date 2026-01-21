#! python3
# pushover.py | 2026-01-21 | Modular Version
# Purpose: Dispatch urgent notifications via Pushover

import requests
import logging

def send_alert(token, user, image_path, title, message, cam_loc=None):
    """
    Dispatches an emergency Pushover alert with an image attachment.
    """
    if not token or not user:
        logging.warning("Pushover keys missing. Skipping alert.")
        return False

    payload = {
        "token": token,
        "user": user,
        "title": title,
        "message": message,
        "priority": 2,          # Emergency: Bypasses silent mode
        "retry": 60,             # Retry every 60s until acknowledged
        "expire": 3600,          # Link expires in 1 hour
        "sound": "persistent"    # Continuous alarm sound
    }

    # Add Google Maps link if coordinates are provided
    if cam_loc:
        payload["url"] = f"https://www.google.com/maps?q={cam_loc[0]},{cam_loc[1]}"
        payload["url_title"] = "View Camera Location"

    try:
        with open(image_path, "rb") as image_file:
            files = {"attachment": ("alert.jpg", image_file, "image/jpeg")}
            response = requests.post(
                "https://api.pushover.net/1/messages.json", 
                data=payload, 
                files=files, 
                timeout=20
            )
            response.raise_for_status()
            logging.info("Pushover alert dispatched successfully.")
            return True
    except Exception as e:
        logging.error(f"Pushover notification failed: {e}")
        return False
