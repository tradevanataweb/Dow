import os
import subprocess
import logging
from urllib.parse import urlparse
from datetime import datetime

DOWNLOAD_DIR = "downloads"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def sanitize_filename(filename):
    return "".join(c if c.isalnum() or c in " ._-" else "_" for c in filename)

def download_content(url: str):
    if not url:
        raise ValueError("Empty URL provided.")

    logging.info(f"Starting download for: {url}")

    domain = urlparse(url).netloc
    date_folder = datetime.now().strftime("%Y-%m-%d")
    save_path = os.path.join(DOWNLOAD_DIR, sanitize_filename(domain), date_folder)

    os.makedirs(save_path, exist_ok=True)

    command = [
        "yt-dlp",
        "--no-playlist",
        "--write-thumbnail",
        "--write-info-json",
        "--output", os.path.join(save_path, "%(title).70s.%(ext)s"),
        url
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        logging.info("Download complete.")

        # Look for merged file in output
        for line in result.stdout.splitlines():
            if "Merging formats into" in line and ".mp4" in line:
                abs_path = line.split('"')[1]  # Extract file path
                rel_path = os.path.relpath(abs_path, DOWNLOAD_DIR)
                logging.info(f"Final video file: {rel_path}")
                return {
                    "status": "success",
                    "output": result.stdout,
                    "video_filename": rel_path  # return this for frontend use
                }

        # If merging line not found, fallback
        return {
            "status": "success",
            "output": result.stdout,
            "video_filename": None  # frontend will handle gracefully
        }

    except subprocess.CalledProcessError as e:
        logging.error(f"Error: {e.stderr}")
        return {"status": "error", "error": e.stderr}
