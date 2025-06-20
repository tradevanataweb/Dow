from flask import Flask, request, jsonify
from downloader import download_content
import os
import logging

app = Flask(__name__)

# Enable logging to show messages in Render logs
logging.basicConfig(level=logging.INFO)
logging.info("✅ Flask backend started and ready to receive requests.")

@app.route("/download", methods=["POST"])
def handle_download():
    data = request.json
    if not data or "url" not in data:
        return jsonify({"error": "Missing 'url' in request."}), 400

    logging.info(f"📥 Received download request for URL: {data['url']}")
    try:
        result = download_content(data["url"])
        return jsonify(result)
    except Exception as e:
        logging.error(f"❌ Error during download: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/status")
def status():
    return jsonify({"message": "✅ Backend is running!"}), 200

# Optional for local testing
# if __name__ == "__main__":
#     app.run(debug=True, port=5000)
