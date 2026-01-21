#!/bin/bash

# install.sh | 2026-01-21 | LookoutConnect Unified Installer
# Target: Linux / Raspberry Pi / Ubuntu

echo "------------------------------------------------"
echo "Starting LookoutConnectV4 Installation..."
echo "------------------------------------------------"

# 1. Update system and install Python pip
echo "[*] Updating system packages..."
sudo apt-get update -y && sudo apt-get install -y python3-pip python3-pil python3-dotenv

# 2. Create Directory Structure
echo "[*] Creating folder structure..."
mkdir -p archive
mkdir -p logs

# 3. Install Python Dependencies
echo "[*] Installing required Python libraries..."
pip3 install requests Pillow python-dotenv

# 4. Create Template .env File
if [ ! -f .env ]; then
    echo "[*] Creating template .env file..."
    cat <<EOF > .env
# --- Camera Configuration ---
CAMERA_IP=192.168.1.100
CAMERA_USER=admin
CAMERA_PASS=password
CAMERA_NAME=Wildfire-Sentinel-01
CAMERA_LOC=22.450,114.080

# --- LookOut AI Platform ---
LOOKOUT_API_KEY=your_lookout_api_key_here

# --- Notification Keys ---
PUSHOVER_APP_TOKEN=your_pushover_token
PUSHOVER_USER_KEY=your_pushover_user_key
NTFY_TOPIC=your_ntfy_topic
OPENWEATHER_API_KEY=your_weather_key

# --- System Timers ---
TIMER_REQUESTS=25
TIMER_WATCHDOG=55

# --- ACS Pro Config ---
AXIS_RULE=WildfireAlert
EOF
    echo "[!] .env created. PLEASE UPDATE IT WITH YOUR REAL KEYS."
else
    echo "[!] .env already exists. Skipping creation."
fi

# 5. Set Permissions
echo "[*] Finalizing permissions..."
chmod +x install.sh

echo "------------------------------------------------"
echo "Installation Complete!"
echo "Next Steps:"
echo "1. Edit your .env file: nano .env"
echo "2. Place LookoutConnect.py, pushover.py, and other modules in this folder."
echo "3. Run: python3 LookoutConnect.py api"
echo "------------------------------------------------"
