# LookoutConnect: AI Wildfire Sentinel

**LookoutConnect** is a professional-grade edge computing middleware designed to bridge standard IP cameras with the **LookOut AI Detection Platform**. It automates the process of capturing imagery, performing AI analysis, and triggering a multi-layered alert system.

## 🏗️ Modular Architecture

The system is built on a "Hub and Spoke" model. The main controller (**Hub**) manages the detection logic and system integrity, while specialized **Modules** handle external services.

* **`lookoutConnect.py`**: The central controller. Manages timers, image capture, AI uploads, and process locking.
* **`pushover.py`**: Dispatches high-priority mobile alerts with image attachments.
* **`ntfy.sh`**: Provides a secondary, low-latency notification channel.
* **`openWeather.py`**: Fetches real-time localized weather data for environmental context.
* **`acsPro.py`**: Interfaces with Axis Camera Station Pro to trigger local pop-up messages, camera liveviews, or alarms.

---

## 🚀 Key Features

* **Network Resilience**: Uses exponential backoff for uploads to handle unstable remote links.
* **System Integrity**: A **Watchdog Timer** monitors every execution cycle. If a network socket hangs, the script hard-terminates to allow a fresh start.
* **Cross-Platform Support**: Uses specialized file-locking (`msvcrt` for Windows, `fcntl` for Linux) to prevent redundant processes.
* **Forensic Logging**: Self-rotating logs and an image archive provide a permanent audit trail of all AI detections.
* **Smart Scheduling**: The `--runs` argument allows the script to run for a specific number of 1-minute duty cycles.

---

## 🛠️ Installation & Setup

### 1. Deploy the Environment

Run the provided `install.sh` script to set up the directory structure and install dependencies:

```bash
chmod +x install.sh
./install.sh

```

### 2. Configure the `.env`

Update the `.env` file with your camera credentials and API keys. This is the **single source of truth** for the entire system.

### 3. Execution Modes

**API Mode (Pull)**: Direct snapshot from the camera URL.

```bash
python3 lookoutConnect.py api --runs 60

```

**FTP Mode (Push)**: Monitor a local directory for new images.

```bash
python3 lookoutConnect.py ftp --resize

```

---

## 📊 Incident Workflow

1. **Capture**: Image is pulled from the camera or detected in the FTP inbox.
2. **Analyze**: Image is optionally resized and uploaded to LookOut AI Detection Platform.
3. **Enrich**: If a wildfire (or other supported object) is detected, localized weather data is fetched.
4. **Alert**:
* **Pushover**: Emergency alarm sounds on mobile devices.
* **ntfy.sh**: Real-time push notification sent.
* **ACS Pro**: Local physical alarm/relay is activated.


5. **Archive**: The evidence image and AI metadata are stored for forensic review.

---

## 🧪 Manual Test Mode

To ensure your system is working correctly before a fire actually occurs, **LookoutConnect** includes a manual test mode. This allows you to bypass the camera network and "push" a specific local image through the entire AI analysis and notification pipeline.

The `--file` argument is used specifically with **FTP mode**. It tells the script: *"Ignore the camera folder; process this specific file instead."*

#### 1. Prepare your Test Image

Find a representative image (preferably one containing smoke or a controlled burn for a positive test) and place it in your script folder. Let's call it `test_fire.jpg`.

#### 2. Execute the Test Command

Run the following command in your terminal or command prompt:

```bash
python3 lookoutConnect.py ftp --file test_fire.jpg

```

#### 3. What to Expect

When you run this command, the script performs the following steps:

1. **Bypasses State Tracking**: It ignores the `.ptr` file, so you can test the same image multiple times.
2. **AI Analysis**: It uploads `test_fire.jpg` to the LookOut platform.
3. **Full Alert Chain**: If the AI detects smoke in your test image, it will trigger the **Pushover** alarm, **ntfy** message, and the **ACS Pro** rule just as it would during a real event.
4. **Logging**: The results will be recorded in `detectionResults.txt` with a "Manual" tag.


#### 💡 Pro-Tip: Verification Checklist

When testing with a local file, verify the following:

* **Pushover**: Does the notification include the "Emergency" repeating sound?
* **Weather**: Does the message correctly display the current temperature from the `openWeather` module?
* **Logs**: Check `archive/detectionResults.txt` to see if the AI confidence scores are being recorded correctly.

---
