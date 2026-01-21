#! python3
# acsPro.py | 2026-01-21 | Modular Version
# Purpose: Activate external triggers on Axis Camera Station (ACS) Pro

import requests,json, urllib3, logging
from requests.auth import HTTPBasicAuth

# Suppress SSL warnings for local network cameras with self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def send_alert(axis_ip, user, password, rule_name, seconds=5):
    """
    Sends an activation command to the Axis Camera Station API.
    """
    if not all([axis_ip, user, password, rule_name]):
        logging.warning("ACS Pro: Missing configuration parameters.")
        return False

    # ACS Pro API endpoint for manual triggers
    url = f"https://{axis_ip}/Acs/Api/TriggerFacade/ActivateDeactivateTrigger"
    
    params = {
        'triggerName': rule_name,
        'deactivateAfterSeconds': str(seconds)
    }
    
    try:
        # Note: params are sent as a JSON string for this specific Axis API
        response = requests.get(
            url, 
            params=json.dumps(params), 
            auth=HTTPBasicAuth(user, password),
            verify=False, 
            timeout=10
        )
        
        if response.status_code == 200:
            logging.info(f"ACS Pro: Trigger '{rule_name}' activated successfully.")
            return True
        else:
            logging.error(f"ACS Pro: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logging.error(f"ACS Pro: Connection error: {e}")
        return False
