# server.py
from flask import Flask, request, jsonify, send_from_directory
from downloader import download_content # downloader.py is also in the root
import os

# IMPORTANT: static_folder points to the 'client/build' folder
app = Flask(__name__, static_folder="client/build", static_url_path="/")

@app.route("/download", methods=["POST"])
def handle_download():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request."}), 400

    print(f"Received download request for URL: {data['url']}") # For debugging
    try:
        result = download_content(data["url"])
        return jsonify(result)
    except Exception as e:
        print(f"Error during download: {e}") # Log the error
        return jsonify({"error": str(e)}), 500 # Return a 500 error if download fails

# This route serves the React frontend's static files
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    # Debugging print statements (optional, remove for production if desired)
    print(f"Requested path for static files: {path}")
    full_path = os.path.join(app.static_folder, path)
    print(f"Attempting to serve: {full_path}")

    # Check if the requested path corresponds to an actual static file (JS, CSS, images, etc.)
    if path != "" and os.path.exists(full_path):
        return send_from_directory(app.static_folder, path)
    else:
        # Otherwise, serve index.html for React Router to handle client-side routes
        index_html_path = os.path.join(app.static_folder, "index.html")
        print(f"Checking for index.html at: {index_html_path}")
        if not os.path.exists(index_html_path):
            # This means the React build didn't generate index.html in 'client/build/'
            print("WARNING: index.html not found in static folder! Frontend build might be missing or misconfigured.")
            return "Internal Server Error: Frontend build not found.", 500 # More descriptive error

        return send_from_directory(app.static_folder, "index.html")

# Remove or comment out this block for production deployment with Gunicorn
# if __name__ == "__main__":
#     app.run(debug=True, port=5000)
