# 📸 Image Upload Utility (Absolute Path Version)

This Python script monitors a specified directory for new image files, optimizes the newest file by conditionally resizing it, and uploads the resulting file via an HTTP POST request to a configured API endpoint. It ensures all temporary files are cleaned up reliably, regardless of upload success or failure.

## 📝 Prerequisites

You must have Python 3.x installed on your system.

This script relies on two external Python libraries:

  * **`requests`**: For robust handling of the HTTP POST upload.
  * **`Pillow` (PIL)**: For image manipulation and resizing.

You can install these dependencies using `pip`:

```bash
pip install requests pillow
```

## ⚙️ Configuration

Before running the script, you must configure the following variables within the `upload_newest_image.py` file:

| Variable | Location | Description |
| :--- | :--- | :--- |
| `SOURCE_PATH` | Top of script | **ABSOLUTE PATH** to the directory where your camera/application saves its image files. **(CRITICAL)** |
| `UPLOAD_URL` | Top of script | The target API endpoint URL for the HTTP POST upload (e.g., `https://lax.pop.roboticscats.com/api/detects?apiKey=...`). |
| `TARGET_RESOLUTION` | Top of script | The desired image resolution for resizing (e.g., `(1920, 1080)`). |
| `TIME_THRESHOLD_MINUTES`| Top of script | The maximum age (in minutes) an image can be to be considered "new" and processed. Older files are ignored. |

## 🚀 Usage

### 1\. Manual Execution

Run the script directly from your terminal:

```bash
python3 upload_newest_image.py
```

### 2\. Automated Scheduling (Cron Job)

To run this script automatically every two minutes (as discussed previously), you should set up a cron job.

1.  **Open your crontab:**

    ```bash
    crontab -e
    ```

2.  **Add the following line:**
    You must use the **absolute path** to both the Python executable and your script, and it is highly recommended to redirect all output to a log file to avoid filling up the system mail queue.

    ```bash
    # Run the script every two minutes (*/2)
    */2 * * * * /usr/bin/python3 /path/to/your/upload_newest_image.py >> /var/log/image_upload.log 2>&1
    ```

    *(Note: Replace `/usr/bin/python3` and `/path/to/your/upload_newest_image.py` with your actual absolute paths.)*

## 💡 Processing Logic & Safety

The script performs the following sequence of operations to ensure reliable and optimized uploads:

1.  **File Discovery & Time Check:**

      * Finds the newest image (`*.jpg`/`*.jpeg`) in the `SOURCE_PATH`.
      * **Breaks and does nothing** if the newest image is older than `TIME_THRESHOLD_MINUTES`.

2.  **Resize and Optimization:**

      * The script attempts to resize the image to `TARGET_RESOLUTION`.
      * It compares the **file size** of the **original image** against the **resized image**.
      * **Optimization:** It selects the file with the **smaller size** for upload, discarding the larger one. This minimizes bandwidth consumption.

3.  **Upload:**

      * Performs an HTTP POST request using the `requests` library with the optimized image file.

4.  **Guaranteed Cleanup (Absolute Safety):**

      * The script uses a `try...finally` block to ensure that any file **created by the script** (i.e., the resized image) is **deleted** from the disk, regardless of whether the upload was successful or failed.
      * **The original source file in the `SOURCE_PATH` is never deleted.**

-----

## 🛑 Troubleshooting

| Error | Likely Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'requests'` | Dependencies are not installed. | Run `pip install requests pillow`. |
| `FileNotFoundError` or unexpected behavior in Cron | Relative paths used in cron or misconfiguration of `SOURCE_PATH`. | Ensure all paths (`SOURCE_PATH`, Python executable, script path) are **absolute paths** (starting with `/`). |
| `requests.exceptions.HTTPError: 400 Bad Request` | The API rejected the upload. | Verify `UPLOAD_URL` is correct, including the `apiKey`. The API may also reject the image if the quality/format is unexpected (unlikely, but possible). |
| Script doesn't seem to run | Cron environment issues. | Check the cron log file (`/var/log/image_upload.log` in the example above) for Python error messages or permission issues. |
