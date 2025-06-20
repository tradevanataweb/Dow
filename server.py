from flask import Flask, request, jsonify
from downloader import download_content

app = Flask(__name__)

@app.route("/download", methods=["POST"])
def handle_download():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request."}), 400

    result = download_content(data["url"])
    return jsonify(result)

@app.route("/", methods=["GET"])
def home():
    return {
        "message": "Downloader API is running. Use POST /download with JSON: { 'url': '...' }"
    }, 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
