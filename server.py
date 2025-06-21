from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS # Import CORS
from downloader import download_content, DOWNLOAD_DIR # Import DOWNLOAD_DIR from downloader
import os
import logging # Import logging

# --- App Setup ---
# React static files will be served from here
app = Flask(__name__, static_folder="client/build", static_url_path="/")

# Enable CORS for all origins on all routes (for development)
# In production, restrict this to your frontend's actual domain(s)
CORS(app)

# --- Logging Configuration ---
# You can use Flask's built-in logger or configure Python's standard logging.
# Here, we'll configure a basic file logger for the server itself.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("server.log"), # Log server activities to a file
        logging.StreamHandler()             # Log to console
    ]
)
# Use app.logger for Flask-specific logging
app.logger.setLevel(logging.INFO)


# --- API Routes ---

@app.route("/download", methods=["POST"])
def handle_download():
    """
    Handles download requests, calls the downloader, and returns a URL to the downloaded file.
    """
    data = request.json
    if not data or "url" not in data:
        app.logger.warning("Received download request with missing 'url' field.")
        return jsonify({"error": "Missing 'url' in request."}), 400

    url_to_download = data["url"]
    app.logger.info(f"Received download request for URL: {url_to_download}")

    try:
        # Call the download_content function from downloader.py
        # IMPORTANT: For production, this should be an asynchronous task (e.g., Celery)
        # to prevent blocking the web server.
        result = download_content(url_to_download)

        if result.get("status") == "error":
            error_message = result.get("error", "An unknown error occurred during download.")
            app.logger.error(f"Download failed for {url_to_download}: {error_message}")
            return jsonify({"status": "error", "error": error_message}), 500

        video_filename = result.get("video_filename")

        if not video_filename:
            app.logger.warning(f"Download successful for {url_to_download} but no specific video filename was returned by downloader.")
            return jsonify({
                "status": "success",
                "message": "Download completed, but could not determine direct video URL. Check server logs."
            }), 200 # Or 202 if it's a background process

        # Construct the URL for the downloaded file
        video_url = f"/downloads/{video_filename}"
        app.logger.info(f"Download successful for {url_to_download}. Video available at: {video_url}")

        return jsonify({
            "status": "success",
            "video_url": video_url,
            "message": "Content downloaded successfully!"
        })

    except Exception as e:
        app.logger.exception(f"An unexpected error occurred while handling download for {url_to_download}") # logs traceback
        return jsonify({"status": "error", "error": f"Internal server error: {str(e)}"}), 500


# Serve downloaded video files
@app.route("/downloads/<path:filename>")
def serve_download(filename):
    """
    Serves downloaded files from the DOWNLOAD_DIR.
    """
    # Ensure the DOWNLOAD_DIR exists and is used
    full_download_path = os.path.abspath(DOWNLOAD_DIR)
    app.logger.info(f"Serving request for downloaded file: {filename} from {full_download_path}")

    # For security, send_from_directory is preferred.
    # as_attachment=False means the browser will try to display/play it.
    # as_attachment=True means the browser will prompt to download it.
    try:
        return send_from_directory(full_download_path, filename, as_attachment=False)
    except FileNotFoundError:
        app.logger.warning(f"Requested downloaded file not found: {filename}")
        return jsonify({"error": "File not found."}), 404
    except Exception as e:
        app.logger.exception(f"Error serving downloaded file {filename}")
        return jsonify({"error": f"Error serving file: {str(e)}"}), 500


# --- Frontend Serving Routes ---

# Serve React frontend (client/build) - handles client-side routing
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    """
    Serves the React frontend's static files.
    For any path not matching a static file, it falls back to index.html for client-side routing.
    """
    # Debugging print statements are replaced with app.logger.info for production readiness
    app.logger.info(f"Requested path for static files: {path}")

    # Construct the full path to the requested file within the static folder
    full_path_in_static = os.path.join(app.static_folder, path)

    # Check if the requested path refers to an actual file in the static folder
    # and it's not the root path (which should always serve index.html initially)
    if path != "" and os.path.exists(full_path_in_static) and os.path.isfile(full_path_in_static):
        return send_from_directory(app.static_folder, path)
    else:
        # If the path doesn't correspond to a static file, serve index.html
        # This is crucial for single-page applications (SPAs) with client-side routing.
        index_html_path = os.path.join(app.static_folder, "index.html")
        app.logger.info(f"Serving index.html for path: {path} (checking at: {index_html_path})")

        if not os.path.exists(index_html_path):
            app.logger.critical("Frontend build missing! index.html not found in static folder.")
            return "Internal Server Error: Frontend build (index.html) not found. Please run 'npm run build' in your client directory.", 500

        return send_from_directory(app.static_folder, "index.html")


# --- Main Application Run ---
if __name__ == "__main__":
    # Ensure the base download directory exists
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000) # Host on 0.0.0.0 to be accessible from other machines
