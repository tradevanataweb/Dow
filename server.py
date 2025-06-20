from flask import Flask, request, jsonify, send_from_directory
from downloader import download_content
import os

app = Flask(__name__, static_folder="../client/build", static_url_path="/")

@app.route("/download", methods=["POST"])
def handle_download():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request."}), 400

    result = download_content(data["url"])
    return jsonify(result)

@app.route("/status")
def status():
    return jsonify({"message": "Backend is running"}), 200

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_react(path):
    if path != "" and os.path.exists(app.static_folder + "/" + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
