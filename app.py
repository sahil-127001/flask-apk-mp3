from flask import Flask, request, render_template, send_from_directory, jsonify
import yt_dlp
import os
import subprocess

app = Flask(__name__)

# Temporary download folder in Render
DOWNLOAD_DIR = "/tmp/music"
FFMPEG_PATH = "/usr/bin/ffmpeg"

# Ensure the temporary directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to download YouTube audio with a thumbnail
def download_audio(url, save_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{save_path}/%(title)s.%(ext)s",
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"},
            {"key": "EmbedThumbnail"},
            {"key": "FFmpegMetadata"},
        ],
        "ffmpeg_location": FFMPEG_PATH,
        "writethumbnail": True,
        "noplaylist": True,
        "progress_hooks": [progress_hook],  # Show progress
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info["title"]

# Show download progress in console
def progress_hook(d):
    if d["status"] == "downloading":
        print(f"Downloading: {d['_percent_str']} complete")

# Route to render the input form
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint to download a song
@app.route("/download", methods=["POST"])
def download_song():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        print("Starting download...")
        video_title = download_audio(url, DOWNLOAD_DIR)
        filename = f"{video_title}.mp3"
        return jsonify({"message": "Download complete", "file_url": f"/music/{filename}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Serve downloaded songs
@app.route("/music/<filename>", methods=["GET"])
def serve_song(filename):
    return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
