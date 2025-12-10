#!/usr/bin/python3

import os
import sys
import glob
from datetime import datetime, timedelta
from PIL import Image
import requests

# --- Global Definitions ---
# Get the absolute path of the directory where this script resides
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Configuration ---
# 1. Source Path: **UPDATE THIS VARIABLE** to the ABSOLUTE path containing your images.
SOURCE_PATH = "/path/to/your/image/directory" 
# Ensure the source path is absolute
SOURCE_PATH = os.path.abspath(SOURCE_PATH)

# 2. API Endpoint URL (Upload Target)
UPLOAD_URL = "https://lax.pop.roboticscats.com/api/detects?apiKey=316f285f2e909ce1b3625bfb755286f5"

# 3. Image Processing Parameters
TARGET_RESOLUTION = (1920, 1080)
CONTENT_TYPE = "image/jpeg"
TIME_THRESHOLD_MINUTES = 5

def find_newest_image(source_dir):
    """Finds the ABSOLUTE path to the newest JPG/JPEG file in the source directory."""
    
    search_pattern = os.path.join(source_dir, "*.[jJ][pP][gG]*")
    list_of_files = glob.glob(search_pattern)
    
    if not list_of_files:
        return None
    
    # Sort files by modification time (mtime) in descending order
    # The max() function returns the absolute path
    latest_file = max(list_of_files, key=os.path.getmtime)
    
    return latest_file

def check_timestamp(file_path, threshold_minutes):
    """Checks if the file was modified within the threshold time."""
    
    file_mtime_epoch = os.path.getmtime(file_path)
    file_mtime = datetime.fromtimestamp(file_mtime_epoch)
    
    time_threshold = datetime.now() - timedelta(minutes=threshold_minutes)
    
    print(f"File Mod Time: {file_mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Threshold Time: {time_threshold.strftime('%Y-%m-%d %H:%M:%S')} ({threshold_minutes} min ago)")
    
    if file_mtime < time_threshold:
        return False
    return True

def format_size(size_bytes):
    """Converts size in bytes to a human-readable format (KB, MB)."""
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} bytes"

def resize_image(original_path, target_resolution, script_directory):
    """
    Resizes the image, compares file sizes, and returns the ABSOLUTE path to the smaller file.
    All new files are created in the script_directory.
    """
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Files are created using ABSOLUTE paths inside the script's directory
    temp_resized_filename = os.path.join(script_directory, f"temp_resized_{timestamp}.jpg")
    
    print(f"\n📐 Resizing image to {target_resolution[0]}x{target_resolution[1]}...")
    
    try:
        original_size = os.path.getsize(original_path)
        print(f"   Original File Size: {format_size(original_size)}")
        
        # 1. Perform Resize and Save to temporary file
        img = Image.open(original_path)
        resized_img = img.resize(target_resolution)
        resized_img.save(temp_resized_filename, "jpeg")
        resized_size = os.path.getsize(temp_resized_filename)
        
        print(f"   Temp Resized Size: {format_size(resized_size)}")

        # 2. Compare Sizes and Select File
        if original_size <= resized_size:
            # Original file is smaller or same size: keep original
            os.remove(temp_resized_filename)
            print("💡 Optimization: Keeping original file as it is smaller or equal in size.")
            return original_path # <-- Returns the ABSOLUTE path to the original
        else:
            # Resized file is smaller: rename the temporary file to the final output name
            final_resized_filename = os.path.join(script_directory, f"camera_snapshot_resized_{timestamp}.jpg")
            os.rename(temp_resized_filename, final_resized_filename)
            print(f"✅ Optimization: Keeping resized file, saved as {final_resized_filename}.")
            return final_resized_filename # <-- Returns the ABSOLUTE path to the resized file
            
    except Exception as e:
        print(f"❌ Error during resizing or comparison: {e}")
        
        # Attempt to clean up temp file if it exists after failure
        if os.path.exists(temp_resized_filename):
            os.remove(temp_resized_filename)
        
        return None

def upload_image(file_path, upload_url, content_type):
    """Uploads the image file using HTTP POST."""
    
    print(f"⬆️ Attempting to upload image ({os.path.basename(file_path)}) to API...")
    # The file_path here is guaranteed to be absolute

    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()

        headers = {'Content-Type': content_type}

        response = requests.post(
            url=upload_url, 
            data=file_data, 
            headers=headers
        )
        
        response.raise_for_status() 

        print(f"✅ Success! Image uploaded.")
        print(f"HTTP Status Code: {response.status_code}")
        print(f"API Response Body: {response.text}")
        return True

    except requests.exceptions.HTTPError as http_err:
        print(f"❌ HTTP Error during upload: {http_err}")
        print(f"HTTP Status Code: {response.status_code}")
        try:
            api_response = response.text
        except Exception:
            api_response = "N/A (could not decode response body)"

        print(f"API Response Body: {api_response}")
        return False
        
    except requests.exceptions.RequestException as req_err:
        print(f"❌ Request Error during upload: {req_err}")
        return False

# --- Main Execution ---

if __name__ == "__main__":
    
    # --- STEP 1: Find Newest File & Check Time ---
    if not os.path.exists(SOURCE_PATH):
        print(f"❌ Error! Source path does not exist: {SOURCE_PATH}")
        sys.exit(1)

    original_file = find_newest_image(SOURCE_PATH)
    file_to_upload = None

    if not original_file:
        print(f"❌ Error! No image file found in {SOURCE_PATH}.")
        sys.exit(0)
    
    print(f"🔍 Found newest image: {os.path.basename(original_file)} (Path: {original_file})")

    if not check_timestamp(original_file, TIME_THRESHOLD_MINUTES):
        print(f"--- Time Check Failed ---")
        print(f"The newest file is older than {TIME_THRESHOLD_MINUTES} minutes. Exiting.")
        sys.exit(0)
        
    print("--- Time Check Passed ---")
    
    # --- STEP 2: Resize and Optimize ---
    file_to_upload = resize_image(original_file, TARGET_RESOLUTION, SCRIPT_DIR)
    
    if not file_to_upload:
        print("❌ Script terminated due to resizing/optimization failure.")
        sys.exit(1)

    # --- STEP 3 & 4: Upload and Guaranteed Cleanup ---
    upload_success = False

    try:
        # Perform the upload
        upload_success = upload_image(file_to_upload, UPLOAD_URL, CONTENT_TYPE)
        
    finally:
        # Guaranteed cleanup block
        print("\n--- Cleanup ---")
        
        if file_to_upload and os.path.exists(file_to_upload):
            # Compare absolute paths to ensure we only delete files created by the script.
            if os.path.abspath(file_to_upload) != os.path.abspath(original_file):
                print(f"🗑️ Guaranteed deletion of processed file: {os.path.basename(file_to_upload)}...")
                try:
                    os.remove(file_to_upload)
                    print("File deleted successfully.")
                except OSError as e:
                    print(f"Error deleting file: {e}")
            else:
                print("Retained original source file (no deletion necessary).")
        else:
            print("No processed file found for final cleanup.")
            
    print(f"\n--- Script Finished (Upload Success: {upload_success}) ---")
