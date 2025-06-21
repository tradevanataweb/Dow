from flask import Flask, request, jsonify, send_from_directory
from downloader import download_content  # Ensure this is working correctly
import os

# React static files will be served from here
app = Flask(__name__, static_folder="client/build", static_url_path="/")

# Route for handling download requests
@app.route("/download", methods=["POST"])
def handle_download():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request."}), 400

    print(f"Received download request for URL: {data['url']}")  # Debugging
    try:
        result = download_content(data["url"])  # result should include 'video_filename'
        video_filename = result.get("video_filename")

        if not video_filename:
            return jsonify({"error": "Download completed but no filename returned."}), 500

        video_url = f"/downloads/{video_filename}"

        return jsonify({
            "status": "success",
            "video_url": video_url
        })

    except Exception as e:
        print(f"Error during download: {e}")
        return jsonify({"error": str(e)}), 500


# Serve downloaded video files for preview and saving
@app.route("/downloads/<path:filename>")
def serve_download(filename):
    return send_from_directory("downloads", filename, as_attachment=False)


# Serve React frontend (client/build)
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    print(f"Requested path for static files: {path}")
    full_path = os.path.join(app.static_folder, path)
    print(f"Attempting to serve: {full_path}")

    if path != "" and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    else:
        index_html_path = os.path.join(app.static_folder, "index.html")
        print(f"Checking for index.html at: {index_html_path}")
        if not os.path.exists(index_html_path):
            print("WARNING: index.html not found in static folder! Frontend build might be missing.")
            return "Internal Server Error: Frontend build not found.", 500

        return send_from_directory(app.static_folder, "index.html")
