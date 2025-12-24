# lookoutConnect.py

**lookoutConnect.py** is a lightweight, production-grade Python middleware designed to bridge standard IP cameras (such as Axis, Hikvision, or Dahua) with the **LookOut Wildfire Detection SaaS**.

It is optimized for edge computing, capable of running on a Raspberry Pi, Mini PC, or any Linux/Windows machine directly connected to the camera network.

---

## 🚀 Key Features

* **Dual Operation Modes:** Supports both **API (Pull)** for active snapshot triggering and **FTP (Push)** for monitoring uploaded files.
* **Edge Optimized:** Extremely low resource footprint; ideal for remote hardware.
* **Network Resilience:** Implements an **Exponential Backoff** retry algorithm and strict timeouts to handle unstable remote links (cellular/radio).
* **Smart Resizing:** Optional `--resize` flag to downscale images to 1080p, reducing bandwidth costs while maintaining detection accuracy.
* **Process Safety:** Built-in **Process Locking** (prevents overlapping runs) and a **Watchdog Timer** (kills hung processes).
* **Automated Logging:** Self-rotating detection logs and local image archiving for forensic evidence.

---

## 📂 System Architecture

The script sits between your local camera hardware and the **LookOut Wildfire Detection SaaS**, managing the heavy lifting of image optimization and transmission reliability.

---

## 🛠️ Installation

1. **Clone the repository** (or download `lookoutConnect.py`).
2. **Install Dependencies:**
```bash
pip install Pillow requests python-dotenv

```


3. **Configure Environment:** Create a `.env` file in the same directory (see [Configuration](https://www.google.com/search?q=%23configuration) below).

---

## ⚙️ Configuration (.env)

Define your specific camera and API settings in a `.env` file:

```env
# LookOut API Settings
LOOKOUT_API_KEY=your_LookOut_camera_endpoint_after_apiKey=

# Camera Credentials (API Mode)
CAMERA_IP=192.168.1.100
CAMERA_USER=admin
CAMERA_PASS=your_password

# Folder Paths (FTP Mode)
SOURCE_PATH=/home/user/ftp/camera_inbox
FTP_ARCHIVE_DIR=/home/user/ftp/detections_archive

```

---

## 📖 How to Use

### 1. API Mode (Pull)

Best if your camera provides an HTTP snapshot URL. The script will request an image directly from the camera.

```bash
python3 lookoutConnect.py api

```

### 2. FTP Mode (Push)

Best if your camera is configured to upload images to a local folder. The script monitors the `SOURCE_PATH` for the newest file.

```bash
python3 lookoutConnect.py ftp

```

### 3. Optional Resizing

To save bandwidth, add the `--resize` flag to downscale the image to 1080p before uploading:

```bash
python3 lookoutConnect.py api --resize

```

---

## 📊 Outputs

* **`detectionResults.txt`**: Located in the archive directory. Records every detection (timestamp, filename, and AI metadata). Automatically rotates when it reaches 5MB.
* **Archive Folder**: Images that result in a positive detection are copied here for permanent storage.
* **`last_processed.ptr`**: Tracks the state in FTP mode to ensure no image is uploaded twice.

---

## ⏲️ Automation (Crontab)

To run the script every minute, add the following to your crontab (`crontab -e`):

```bash
# Example: Run FTP mode every minute with resizing enabled
* * * * * /usr/bin/python3 /path/to/lookoutConnect.py ftp --resize >> /path/to/cron.log 2>&1

```

---

## 📝 License

This project is provided as freeware for use with the LookOut Wildfire Detection SaaS.
