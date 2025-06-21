import os
import subprocess
import logging
from urllib.parse import urlparse
from datetime import datetime
import time
import shutil
import json
import psutil # Added for disk space monitoring

# --- Configuration ---
DOWNLOAD_DIR = "downloads"
DISK_SPACE_THRESHOLD_PERCENT = 90  # Warn/Abort if disk usage exceeds this percentage
CLEANUP_DAYS_OLD = 30              # Delete files older than this many days

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("downloader.log"), # Log to a file
        logging.StreamHandler()                 # Log to console
    ]
)

# --- Helper Functions ---

def sanitize_filename(filename):
    """
    Sanitizes a string to be used as a filename or path component.
    Removes/replaces characters that are not alphanumeric, space, dot, underscore, or hyphen.
    """
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in filename)

def check_disk_usage(path: str = os.getcwd(), threshold_percent: int = DISK_SPACE_THRESHOLD_PERCENT) -> bool:
    """
    Checks disk usage for a given path and logs a warning if it exceeds a threshold.
    Returns True if usage is above threshold, False otherwise.
    """
    try:
        # psutil.disk_usage checks the filesystem that 'path' resides on.
        # Use os.path.abspath to ensure we're checking the correct root partition.
        abs_path = os.path.abspath(path)
        disk_usage = psutil.disk_usage(abs_path)
        used_percent = disk_usage.percent
        free_gb = disk_usage.free / (1024**3) # Convert bytes to GB

        logging.info(f"Disk usage for {abs_path}: {used_percent:.2f}% used, {free_gb:.2f} GB free.")

        if used_percent >= threshold_percent:
            logging.warning(f"CRITICAL: Disk usage for {abs_path} is at {used_percent:.2f}%, exceeding threshold of {threshold_percent}%.")
            return True
        return False
    except FileNotFoundError:
        logging.error(f"Cannot check disk usage: Path '{path}' does not exist.")
        return False
    except Exception as e:
        logging.error(f"Error checking disk usage for {path}: {e}")
        return False

def clean_old_downloads(days_old: int = CLEANUP_DAYS_OLD):
    """
    Deletes files and empty directories in DOWNLOAD_DIR older than a specified number of days.
    This function should ideally be run as a separate scheduled job (e.g., cron).
    """
    if not os.path.exists(DOWNLOAD_DIR):
        logging.info(f"Download directory '{DOWNLOAD_DIR}' does not exist. No cleanup needed.")
        return

    cutoff_time = time.time() - (days_old * 24 * 60 * 60) # Convert days to seconds

    logging.info(f"Starting cleanup of downloads older than {days_old} days in {DOWNLOAD_DIR}")
    deleted_files_count = 0
    deleted_dirs_count = 0

    # Walk from bottom up to ensure empty directories can be removed
    for root, dirs, files in os.walk(DOWNLOAD_DIR, topdown=False):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                # Check modification time, ensure file still exists to prevent race conditions
                if os.path.exists(filepath) and os.stat(filepath).st_mtime < cutoff_time:
                    os.remove(filepath)
                    logging.info(f"Deleted old file: {filepath}")
                    deleted_files_count += 1
            except OSError as e:
                logging.error(f"Error deleting file {filepath}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error during file deletion {filepath}: {e}")


        for name in dirs:
            dirpath = os.path.join(root, name)
            try:
                # After files are deleted, check if directory is empty before removing
                if os.path.exists(dirpath) and not os.listdir(dirpath):
                    os.rmdir(dirpath)
                    logging.info(f"Deleted empty directory: {dirpath}")
                    deleted_dirs_count += 1
            except OSError as e:
                logging.error(f"Error deleting directory {dirpath}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error during directory deletion {dirpath}: {e}")

    logging.info(f"Cleanup finished. Deleted {deleted_files_count} files and {deleted_dirs_count} empty directories.")

# --- Main Download Function ---

def download_content(url: str):
    """
    Downloads content from the given URL using yt-dlp, saving it to an organized directory structure.
    Includes disk space check before download.
    """
    if not url:
        logging.error("Empty URL provided for download.")
        return {"status": "error", "error": "Empty URL provided."}

    # Ensure the base download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Check disk space before proceeding
    if check_disk_usage(path=DOWNLOAD_DIR, threshold_percent=DISK_SPACE_THRESHOLD_PERCENT):
        logging.error(f"Disk space is critically low ({DISK_SPACE_THRESHOLD_PERCENT}% threshold). Aborting download for {url}.")
        return {"status": "error", "error": f"Disk space critically low. Please free up space. Current usage: {psutil.disk_usage(os.path.abspath(DOWNLOAD_DIR)).percent:.2f}%."}

    logging.info(f"Starting download for: {url}")

    domain = urlparse(url).netloc
    date_folder = datetime.now().strftime("%Y-%m-%d")
    # Using sanitize_filename for domain to create valid directory names
    save_path = os.path.join(DOWNLOAD_DIR, sanitize_filename(domain), date_folder)

    os.makedirs(save_path, exist_ok=True)
    logging.info(f"Saving content to: {save_path}")

    # yt-dlp command with --print-json for reliable output parsing
    command = [
        "yt-dlp",
        "--no-playlist",          # Download single video, not entire playlist
        "--write-thumbnail",      # Download thumbnail
        "--write-info-json",      # Download info JSON
        "--output", os.path.join(save_path, "%(title).70s.%(ext)s"), # Output format
        "--print-json",           # Print final video metadata as JSON to stdout
        url
    ]

    try:
        # Use capture_output=True to get stdout and stderr
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        logging.info("Download command executed successfully.")

        video_filename = None
        yt_dlp_info = None

        # Parse the JSON output from yt-dlp. It's usually the last complete JSON object.
        # yt-dlp can print multiple lines (progress, etc.) before the final JSON.
        json_lines = [line for line in result.stdout.splitlines() if line.strip().startswith('{') and line.strip().endswith('}')]
        if json_lines:
            try:
                # Attempt to parse the last JSON object, which typically contains final file info
                yt_dlp_info = json.loads(json_lines[-1])
                # _filename is the key for the final file path in yt-dlp's JSON output
                if '_filename' in yt_dlp_info:
                    abs_path = yt_dlp_info['_filename']
                    # Ensure the path is relative to DOWNLOAD_DIR if it's within it
                    if os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_DIR)):
                        video_filename = os.path.relpath(abs_path, DOWNLOAD_DIR)
                    else:
                        # Fallback if _filename is outside expected dir (shouldn't happen with --output)
                        video_filename = abs_path
                    logging.info(f"Final video file identified from JSON: {video_filename}")
                else:
                    logging.warning("'_filename' key not found in yt-dlp JSON output.")
            except json.JSONDecodeError as e:
                logging.warning(f"Could not decode yt-dlp JSON output: {e}")
            except Exception as e:
                logging.warning(f"Error processing yt-dlp JSON output: {e}")
        else:
            logging.warning("No complete JSON object found in yt-dlp stdout. Falling back to stdout parsing.")
            # Fallback for older yt-dlp versions or unusual outputs
            for line in result.stdout.splitlines():
                if "Merging formats into" in line and (".mp4" in line or ".mkv" in line):
                    try:
                        # Extract file path, assuming it's enclosed in quotes
                        start = line.find('"') + 1
                        end = line.rfind('"')
                        if start > 0 and end > start:
                            abs_path = line[start:end]
                            if os.path.abspath(abs_path).startswith(os.path.abspath(DOWNLOAD_DIR)):
                                video_filename = os.path.relpath(abs_path, DOWNLOAD_DIR)
                            else:
                                video_filename = abs_path # Keep as absolute if outside for some reason
                            logging.info(f"Final video file identified from stdout (fallback): {video_filename}")
                            break # Found it, no need to check other lines
                    except Exception as e:
                        logging.warning(f"Error parsing merge line: {e}")

        if video_filename is None:
            logging.warning("Could not determine final video filename from yt-dlp output.")

        return {
            "status": "success",
            "output": result.stdout, # Include full stdout for debugging if needed
            "video_filename": video_filename # Relative path for frontend use
        }

    except subprocess.CalledProcessError as e:
        logging.error(f"yt-dlp command failed with error code {e.returncode}: {e.stderr}")
        return {"status": "error", "error": e.stderr}
    except FileNotFoundError:
        logging.error("yt-dlp command not found. Make sure yt-dlp is installed and in your PATH.")
        return {"status": "error", "error": "yt-dlp not found. Please install it."}
    except Exception as e:
        logging.error(f"An unexpected error occurred during download: {e}")
        return {"status": "error", "error": str(e)}

# --- Main Execution Block (for direct script execution/testing) ---
if __name__ == "__main__":
    # This block runs only when the script is executed directly (e.g., python downloader.py)
    # It's useful for testing the cleanup and disk checks independently.
    # In a web API, `download_content` would be called by your Flask/FastAPI route.
    # The cleanup function should ideally be run as a separate scheduled job.

    # Ensure base download directory exists before any operations
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Example of how you might integrate disk checks:
    logging.info("--- Starting Disk Space Check ---")
    if check_disk_usage(path=DOWNLOAD_DIR): # Check disk where downloads occur
        logging.warning("Disk usage is high. Consider running cleanup or expanding storage.")
    logging.info("--- Disk Space Check Complete ---")

    # Example of how to trigger cleanup manually (or via cron)
    logging.info("--- Starting Scheduled Cleanup ---")
    clean_old_downloads() # Deletes files older than CLEANUP_DAYS_OLD
    logging.info("--- Scheduled Cleanup Complete ---")

    # Example of how to call download_content (for testing purposes)
    # Note: In a real API, this would be triggered by an HTTP request.
    # test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ" # Example YouTube URL
    # logging.info(f"\n--- Attempting to download test URL: {test_url} ---")
    # result = download_content(test_url)
    # logging.info(f"Download Result: {json.dumps(result, indent=2)}")
    # logging.info("--- Test Download Complete ---\n")
