from flask import Flask, request, render_template, send_from_directory, jsonify
import requests
import os
import subprocess
from pathlib import Path

app = Flask(__name__)

# Temporary download folder in Render
DOWNLOAD_DIR = "/tmp/music"
FFMPEG_PATH = "/usr/bin/ffmpeg"

# Ensure the temporary directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to get video title and MP3 download link from an external API
def get_video_info(url):
    api_url = f"https://yt-download.org/api/button/mp3?url={url}"
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        data = response.json()
        return {"title": data.get("title", "Unknown"), "mp3_url": data.get("link")}
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

# Function to fetch video thumbnail (YouTube auto-generates thumbnails)
def get_thumbnail_url(video_id):
    return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"

# Function to download a file (MP3 or Thumbnail) with progress
def download_file(url, save_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    downloaded_size = 0

    if response.status_code == 200:
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
                downloaded_size += len(chunk)
                if total_size > 0:
                    progress = (downloaded_size / total_size) * 100
                    print(f"Downloading {save_path}: {progress:.2f}%")
        return True
    return False

# Function to merge MP3 and Thumbnail using FFmpeg
def merge_audio_thumbnail(mp3_path, thumbnail_path, output_path):
    command = [
        FFMPEG_PATH, "-i", mp3_path, "-i", thumbnail_path,
        "-map", "0:a", "-map", "1:v", "-c:a", "copy", "-c:v", "mjpeg",
        "-id3v2_version", "3", "-metadata", "title=YouTube Download",
        output_path
    ]
    subprocess.run(command, check=True)

# Route to render the form to input YouTube URL
@app.route("/")
def index():
    return render_template("index.html")

# Endpoint to handle YouTube download and merge thumbnail
@app.route("/download", methods=["POST"])
def download_song():
    url = request.form.get("url")
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Extract Video ID
    video_id = url.split("v=")[-1].split("&")[0]

    # Get video title and MP3 download link
    result = get_video_info(url)
    if "error" in result:
        return jsonify(result), 500

    mp3_url = result.get("mp3_url")
    video_title = result.get("title").replace("/", "-")  # Ensure valid filename

    if not mp3_url:
        return jsonify({"error": "Failed to get MP3 link"}), 500

    # File paths
    mp3_path = os.path.join(DOWNLOAD_DIR, f"{video_title}.mp3")
    thumbnail_path = os.path.join(DOWNLOAD_DIR, f"{video_title}.jpg")
    final_mp3_path = os.path.join(DOWNLOAD_DIR, f"{video_title}_final.mp3")

    # Download MP3 with progress
    print(f"Downloading MP3: {video_title}")
    if not download_file(mp3_url, mp3_path):
        return jsonify({"error": "Failed to download MP3"}), 500

    # Download Thumbnail
    thumbnail_url = get_thumbnail_url(video_id)
    print(f"Downloading Thumbnail: {video_title}")
    if not download_file(thumbnail_url, thumbnail_path):
        return jsonify({"error": "Failed to download thumbnail"}), 500

    # Merge MP3 and Thumbnail
    print(f"Merging MP3 and Thumbnail: {video_title}")
    try:
        merge_audio_thumbnail(mp3_path, thumbnail_path, final_mp3_path)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"FFmpeg error: {e}"}), 500

    return jsonify({"message": "Download complete", "file_url": f"/music/{video_title}_final.mp3"}), 200

# Serve merged MP3 files
@app.route("/music/<filename>", methods=["GET"])
def serve_song(filename):
    return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)
