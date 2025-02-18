from flask import Flask, request, render_template, send_from_directory, jsonify
import yt_dlp
import os
from pathlib import Path
import tempfile

app = Flask(__name__)

# Temporary download folder in Render
DOWNLOAD_DIR = '/tmp/music'
FFMPEG_PATH = '/usr/bin/ffmpeg'  # Adjust path if necessary for Render environment

# Ensure the temporary directory exists
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Function to download song with cover art
def download_song_with_cover_art(url, save_path):
    save_path = Path(save_path)
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [
            {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'},
            {'key': 'EmbedThumbnail', 'already_have_thumbnail': False},
            {'key': 'FFmpegMetadata'},
        ],
        'ffmpeg_location': FFMPEG_PATH,
        'noplaylist': True,
        'writethumbnail': True,
        'prefer_ffmpeg': True,
        'postprocessor_args': ['-id3v2_version', '3'],
        'outtmpl': str(save_path / '%(title)s.%(ext)s'),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# Route to render the form to input YouTube URL
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint to handle the form submission and download the song
@app.route('/download', methods=['POST'])
def download_song():
    url = request.form.get('url')
    if not url:
        return "Error: No URL provided", 400
    try:
        # Download song and save it in the DOWNLOAD_DIR
        download_song_with_cover_art(url, DOWNLOAD_DIR)
        
        # Get the name of the file that was downloaded
        filename = os.listdir(DOWNLOAD_DIR)[0]  # Assume only one file is downloaded
        return jsonify({"message": "Download complete", "file_url": f"/music/{filename}"}), 200
    except Exception as e:
        return f"Error: {e}", 500

# Serve downloaded songs publicly
@app.route('/music/<filename>', methods=['GET'])
def serve_song(filename):
    return send_from_directory(DOWNLOAD_DIR, filename)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8000)
