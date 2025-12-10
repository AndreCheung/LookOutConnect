# 📸 Optimized Image Processing & Upload Script

This Bash script is designed for automated, event-driven processing. It monitors a specified directory for new images, optimizes the newest image by conditionally resizing it based on file size, and uploads the resulting file via an HTTP POST request to a configured API endpoint.

## 📝 Prerequisites

This script requires several standard Linux utilities and the **ImageMagick** suite to be installed on your system.

### Required Utilities

| Tool | Purpose | Installation (Debian/Ubuntu Example) |
| :--- | :--- | :--- |
| **`bash`** | Script execution | Standard |
| **`curl`** | HTTP file upload | `sudo apt install curl` |
| **`date`** | Time comparison (Epoch time) | Standard |
| **`find`** | File discovery and filtering | Standard |
| **`stat`** | File size retrieval | Standard |
| **`bc`** | Floating point math for size formatting | `sudo apt install bc` |
| **`convert`** | Image resizing and manipulation (ImageMagick) | `sudo apt install imagemagick` |

## ⚙️ Configuration

Before running the script, you **must** configure the following variables at the top of the script file:

| Variable | Description | Example Value |
| :--- | :--- | :--- |
| `SOURCE_PATH` | **ABSOLUTE PATH** to the directory where your images are saved. | `/var/camera/snapshots` |
| `UPLOAD_URL` | The target API endpoint URL for the HTTP POST upload. | `https://lax.pop.roboticscats.com/api/detects?apiKey=...` |
| `TARGET_RESOLUTION` | The exact resolution for resizing if needed. | `"1920x1080"` |
| `TIME_THRESHOLD_MINUTES`| The maximum age (in minutes) an image can be to be processed. | `5` |

## 🚀 Usage

### 1\. Save and Set Permissions

1.  Save the code as a file (e.g., `process_and_upload.sh`).
2.  Grant execution permissions:
    ```bash
    chmod +x process_and_upload.sh
    ```

### 2\. Automated Scheduling (Cron Job)

This script is highly optimized for being run as a periodic cron job. It includes checks to prevent redundant uploads of old files.

1.  **Open your crontab:**

    ```bash
    crontab -e
    ```

2.  **Add the following line:**
    This example runs the script every two minutes (`*/2`). **Use the absolute path** to your script and redirect output for logging.

    ```bash
    # Run the processing script every two minutes
    */2 * * * * /path/to/your/process_and_upload.sh >> /var/log/image_upload.log 2>&1
    ```

## 💡 Processing Logic & Optimization

The script executes a specific, optimized sequence to handle image files:

1.  **File Discovery & Time Check (Step 1):**

      * The script uses the `find` command to efficiently locate the newest JPG/JPEG file within the `SOURCE_PATH`.
      * **Crucial Filter:** It uses the `-mmin -${TIME_THRESHOLD_MINUTES}` flag to ensure the newest file was created within the defined time window. **If no new file is found, the script gracefully exits without doing anything.**

2.  **Resize and Optimization (Step 2):**

      * If a new file is found, the script attempts to resize it using ImageMagick's `convert`.
      * **File Size Optimization:** The script compares the file size of the **original image** against the **newly resized image**.
      * It selects the file with the **smaller size** for the final upload, discarding the larger one. This prevents bandwidth waste if resizing increases the file size (e.g., due to compression issues).

3.  **Upload (Step 3):**

      * The optimized file is uploaded via `curl` using the raw binary data (`--data-binary`) method.

4.  **Guaranteed Cleanup:**

      * The script ensures that any file **created by the script** (i.e., the resized file saved locally) is deleted upon completion.
      * **Safety Check:** The original source file in the `SOURCE_PATH` is **never** deleted.

## 🛑 Troubleshooting

| Issue | Likely Cause | Solution |
| :--- | :--- | :--- |
| `bc: command not found` | The math utility is missing. | Run `sudo apt install bc` (or equivalent for your OS). |
| `convert: command not found` | ImageMagick is not installed. | Run `sudo apt install imagemagick`. |
| Script fails to find files in Cron | Relative paths used or incorrect `SOURCE_PATH`. | Ensure `SOURCE_PATH` is an **absolute path** and that your Cron entry uses absolute paths. |
| `curl` HTTP 400 or 500 error | API rejection or connectivity issues. | Check the `UPLOAD_URL` and `apiKey`. Review the `API Response Body` in the log output for clues. |
