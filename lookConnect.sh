#!/bin/bash

# --- Configuration ---
# 1. Source Path: **UPDATE THIS VARIABLE** to the directory containing your images.
SOURCE_PATH="/path/to/your/image/directory" 

# 2. API Endpoint URL (Upload Target)
UPLOAD_URL="/URL/to/your/lookout/camera/endpoint"

# 3. Image Processing Parameters
TARGET_RESOLUTION="1920x1080"
CONTENT_TYPE="image/jpeg"
TIME_THRESHOLD_MINUTES=5
TEMP_RESIZED_PREFIX="temp_resized_"

# --- Helper Functions ---

format_size() {
    # Converts bytes to human-readable format (KB, MB)
    local size_bytes=$1
    if (( size_bytes >= 1048576 )); then
        printf "%.2f MB" $(echo "scale=2; $size_bytes / 1048576" | bc)
    elif (( size_bytes >= 1024 )); then
        printf "%.2f KB" $(echo "scale=2; $size_bytes / 1024" | bc)
    else
        printf "%d bytes" $size_bytes
    fi
}

# --- Script Logic: Find Newest File and Check Timestamp ---

echo "🔍 STEP 1: Finding the newest image in ${SOURCE_PATH}..."

# Use find to locate files modified within the last N minutes AND sort by time.
# This is more robust than relying solely on `ls` output parsing.
# The '+${TIME_THRESHOLD_MINUTES}' tells find to look for files older than N minutes.
ORIGINAL_FILE=$(find "${SOURCE_PATH}" -maxdepth 1 -type f \
    \( -iname "*.jpg" -o -iname "*.jpeg" \) \
    -mmin -${TIME_THRESHOLD_MINUTES} \
    -print0 | xargs -0 ls -t 2>/dev/null | head -n 1)

# Check if a file was found
if [ -z "${ORIGINAL_FILE}" ]; then
    echo "--- Time Check Failed ---"
    echo "No image file (*.jpg, *.jpeg) found in ${SOURCE_PATH} created within the last ${TIME_THRESHOLD_MINUTES} minutes."
    echo "Breaking and doing nothing."
    echo
    exit 0 # Exit successfully (do nothing)
fi

echo "✅ Success! Found newest image: **$(basename "${ORIGINAL_FILE}")**"
ORIGINAL_SIZE_BYTES=$(stat -c%s "${ORIGINAL_FILE}")
echo "Original file size: $(format_size "${ORIGINAL_SIZE_BYTES}")"

# --- Script Logic: Resize and Optimize ---
    
echo ""
echo "📐 STEP 2: Resizing, Comparing, and Optimizing..."
    
# Check if 'convert' (ImageMagick) is available
if ! command -v convert &> /dev/null; then
    echo "❌ Error! ImageMagick 'convert' tool not found. Cannot resize."
    echo "Exiting script."
    echo
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEMP_RESIZED_FILE="${TEMP_RESIZED_PREFIX}${TIMESTAMP}.jpg"
FILE_TO_UPLOAD="${ORIGINAL_FILE}" # Default to the original file

# 1. Perform Resize
convert "${ORIGINAL_FILE}" -resize "${TARGET_RESOLUTION}!" "${TEMP_RESIZED_FILE}"
RESIZE_EXIT_CODE=$?

if [ ${RESIZE_EXIT_CODE} -eq 0 ]; then
    RESIZED_SIZE_BYTES=$(stat -c%s "${TEMP_RESIZED_FILE}")
    echo "Temp Resized Size: $(format_size "${RESIZED_SIZE_BYTES}")"
    
    # 2. Compare Sizes
    if [ ${ORIGINAL_SIZE_BYTES} -le ${RESIZED_SIZE_BYTES} ]; then
        # Original is smaller or equal
        rm -f "${TEMP_RESIZED_FILE}"
        echo "💡 Optimization: Keeping original file as it is smaller or equal in size."
        FILE_TO_UPLOAD="${ORIGINAL_FILE}"
    else
        # Resized is smaller: Rename the temp file to the final output name
        FINAL_RESIZED_FILE="camera_snapshot_resized_${TIMESTAMP}.jpg"
        mv "${TEMP_RESIZED_FILE}" "${FINAL_RESIZED_FILE}"
        echo "✅ Optimization: Keeping resized file, saved as ${FINAL_RESIZED_FILE}."
        FILE_TO_UPLOAD="${FINAL_RESIZED_FILE}"
    fi
else
    # Resize failed
    rm -f "${TEMP_RESIZED_FILE}"
    echo "❌ Error! Image resizing failed (ImageMagick exit code: ${RESIZE_EXIT_CODE}). Cannot proceed with upload."
    echo
    exit 1
fi

# --- Script Logic: Upload ---

echo ""
echo "⬆️ STEP 3: Attempting to upload image (File: $(basename "${FILE_TO_UPLOAD}")) to API..."

# Use curl for HTTP POST file upload
UPLOAD_RESPONSE=$(curl -s -X POST \
                        -H "Content-Type: ${CONTENT_TYPE}" \
                        --data-binary @"${FILE_TO_UPLOAD}" \
                        "${UPLOAD_URL}" \
                        --write-out "%{http_code}")

UPLOAD_EXIT_CODE=$?

# Separate API response body from the HTTP code
HTTP_CODE=${UPLOAD_RESPONSE: -3}
API_RESPONSE=${UPLOAD_RESPONSE%???}

UPLOAD_SUCCESS=0
if [ ${UPLOAD_EXIT_CODE} -eq 0 ] && [ ${HTTP_CODE} -ge 200 ] && [ ${HTTP_CODE} -lt 300 ]; then
    UPLOAD_SUCCESS=1
    echo "✅ Success! Image uploaded."
    echo "HTTP Status Code: ${HTTP_CODE}"
    echo "API Response Body: ${API_RESPONSE}"
else
    echo "❌ Error! Image upload failed."
    echo "Curl Exit Code: ${UPLOAD_EXIT_CODE}"
    echo "HTTP Status Code: ${HTTP_CODE}"
    echo "API Response Body: ${API_RESPONSE}"
fi

# --- Script Logic: Guaranteed Cleanup ---

echo "\n--- Cleanup ---"

# Check 1: Ensure we have a file path to check
if [ -n "${FILE_TO_UPLOAD}" ] && [ -e "${FILE_TO_UPLOAD}" ]; then
    # Check 2: ONLY delete the file if its path is NOT the original source file path.
    # This prevents deletion of the camera's source file.
    if [ "${FILE_TO_UPLOAD}" != "${ORIGINAL_FILE}" ]; then
        echo "🗑️ Guaranteed deletion of processed file: $(basename "${FILE_TO_UPLOAD}")..."
        rm -f "${FILE_TO_UPLOAD}"
        echo "File deleted successfully."
    else
        echo "Retained original source file (no deletion necessary)."
    fi
else
    echo "No processed file found for final cleanup."
fi

echo
