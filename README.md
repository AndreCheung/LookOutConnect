# LookoutConnect.py

**LookoutConnect.py** is a high-performance, lightweight Python middleware designed to bridge standard IP cameras (Axis, Hikvision, Dahua, etc.) with the **LookOut AI Wildfire Detection Platform**.

The latest version introduces critical emergency alerting via **Pushover** and advanced manual file handling, making it a professional-grade tool for wildfire sentinels.

---

## 🚀 Advanced Capabilities

* **Network Resilience:** Optimized for remote sites using cellular or radio links. Employs an **Exponential Backoff** algorithm to retry failed uploads without overwhelming unstable connections.
* **Smart Bandwidth Management:** Includes an optional `--resize` flag to downscale images to 1080p using high-quality Lanczos resampling, saving data costs on metered links.
* **System Integrity:** Built-in **Process Locking** prevents concurrent execution, while a **Watchdog Timer** kills hung processes after 55 seconds (default value) to ensure system availability.
* **Pushover Emergency Alerts:** Integrated support for the Pushover API. AI detections trigger **Priority 2 (Emergency)** mobile alerts that bypass silent modes and repeat until acknowledged.
* **Manual Override:** Allows users to specify a single file for upload using the `--file` flag, bypassing automatic polling for testing or forensic re-analysis.

---

## 📂 Outputs & Forensic Logs

* **`detectionResults.txt`**: A persistent heartbeat log recording timestamps, filenames, and AI metadata (coordinates/scores). Automatically rotates at 5MB.
* **Image Archiving**: In **API Mode**, images that result in a positive detection are automatically copied to the archive directory for forensic evidence.
* **State Tracking (`.ptr`)**: Maintains a pointer to the last processed file in FTP mode to prevent duplicate uploads after a script restart or system reboot.

---

## 💻 Deployment

LookoutConnect is designed for the **Edge**. Its lightweight footprint makes it ideal for:

* **Raspberry Pi** (All models)
* **Mini PCs** (Intel NUC, etc.)
* **Existing Field PCs** directly connected to the camera network.

---

## 🛠️ Installation

1. **Install Dependencies:**
```bash
pip install Pillow requests python-dotenv

```


2. **Configure Environment:** Create a `.env` file in the script directory (see below).

---

## ⚙️ Configuration (.env)

```env

# Camera Credentials (API Mode)
CAMERA_NAME=Mountain-Watch-01
CAMERA_IP=192.168.1.100
CAMERA_USER=admin
CAMERA_PASS=your_password
CAMERA_LOC=lat,long

# Paths (FTP Mode)
SOURCE_PATH=/home/user/ftp/images
ARCHIVE_DIR=/home/user/ftp/archive

# LookOut Wildfire Detection SDaaS Camera Endpoint (API key)
LOOKOUT_API_KEY=your_api_key

# ntfy API Key
NTFY_TOPIC=your_topic

# Pushover Alerts
PUSHOVER_APP_TOKEN=your_app_token
PUSHOVER_USER_KEY=your_user_key

# Watchdog Timer Threshold
TIMER_REQUESTS=25
TIMER_WATCHDOG=55

# OpenWeather
OPENWEATHER_API_KEY=your_api_key

```

---

## 📖 How to Use

### 1. Choose Your Mode

* **API Mode**: The script "pulls" a snapshot from the camera via HTTP.
* **FTP Mode**: The script "watches" a folder for images "pushed" by the camera or NVR.

### 2. Execute

Run the script manually or via **Cron job** every minute:

**Standard API Run:**

```bash
python3 LookoutConnect.py api

```

**FTP Mode with Bandwidth Saving:**

```bash
python3 LookoutConnect.py ftp --resize

```

**Manual File Upload (Override):**

```bash
python3 LookoutConnect.py ftp --file /path/to/test_fire.jpg

```

---

## ⏲️ Automation (Crontab)

To automate, run `crontab -e` and add:

```bash
* * * * * /usr/bin/python3 /absolute/path/to/LookoutConnect.py ftp --resize >> /var/log/lookout.log 2>&1

```
