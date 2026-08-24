#!/usr/bin/env python3
"""
Local web tool to swap a video's audio for a fixed background track.

Anyone on your machine (or your local network) can open a browser,
upload an .mp4, and download back a version with the new audio.

Setup (one time):
    pip install flask moviepy

    Put your background audio file in the same folder as this script
    and name it "background_audio.mp3" (or change AUDIO_PATH below).

Run:
    python app.py

Then open:
    http://localhost:5000        (on this machine)
    http://<your-laptop-ip>:5000 (from another device on the same Wi-Fi)

    To find your laptop's IP: `ipconfig` (Windows) or `ifconfig`/`ip a` (Mac/Linux)
"""

import math
import os
import uuid

from flask import Flask, request, render_template_string, send_file, url_for, redirect, flash

from moviepy import (
    VideoFileClip,
    AudioFileClip,
    concatenate_audioclips,
)

# ---- Configuration ----
AUDIO_PATH = "background_audio.mp3"   # <- your fixed background track lives here
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500 MB upload limit

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "change-this-to-anything-random"
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

PAGE = """
<!doctype html>
<html>
<head>
  <title>Video Audio Swapper</title>
  <style>
    body { font-family: sans-serif; max-width: 560px; margin: 60px auto; padding: 0 20px; }
    h1 { font-size: 22px; }
    .box { border: 2px dashed #ccc; padding: 30px; text-align: center; border-radius: 8px; }
    input[type=file] { margin: 20px 0; }
    button { background: #222; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 15px; }
    button:hover { background: #444; }
    .flash { background: #fee; border: 1px solid #f99; padding: 10px; border-radius: 6px; margin-bottom: 16px; }
    .done { background: #efe; border: 1px solid #9c9; padding: 14px; border-radius: 6px; margin-top: 20px; }
  </style>
</head>
<body>
  <h1>Video Audio Swapper</h1>
  <p>Upload an .mp4 video and get it back with the background track added.</p>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for m in messages %}<div class="flash">{{ m }}</div>{% endfor %}
    {% endif %}
  {% endwith %}

  <div class="box">
    <form method="post" action="/upload" enctype="multipart/form-data">
      <input type="file" name="video" accept=".mp4,.mov,.mkv,.avi,.webm" required>
      <br>
      <button type="submit">Upload &amp; Process</button>
    </form>
  </div>

  {% if download_url %}
  <div class="done">
    ✅ Done! <a href="{{ download_url }}">Download your video</a>
  </div>
  {% endif %}
</body>
</html>
"""


def loop_audio_to_length(audio: AudioFileClip, target_duration: float) -> AudioFileClip:
    if audio.duration >= target_duration:
        return audio.subclipped(0, target_duration)
    n_loops = math.ceil(target_duration / audio.duration)
    looped = concatenate_audioclips([audio] * n_loops)
    return looped.subclipped(0, target_duration)


def process_video(input_path: str, output_path: str):
    video = VideoFileClip(input_path)
    audio = AudioFileClip(AUDIO_PATH)
    new_audio = loop_audio_to_length(audio, video.duration)
    final = video.with_audio(new_audio)
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        logger=None,
    )
    video.close()
    audio.close()
    final.close()


@app.route("/")
def index():
    return render_template_string(PAGE, download_url=None)


@app.route("/upload", methods=["POST"])
def upload():
    if not os.path.isfile(AUDIO_PATH):
        flash(f"Background audio file not found on the server: {AUDIO_PATH}")
        return redirect(url_for("index"))

    file = request.files.get("video")
    if not file or file.filename == "":
        flash("Please choose a video file.")
        return redirect(url_for("index"))

    job_id = uuid.uuid4().hex[:10]
    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    input_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")
    output_filename = f"{job_id}_with_audio{ext}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    file.save(input_path)

    try:
        process_video(input_path, output_path)
    except Exception as e:
        flash(f"Processing failed: {e}")
        return redirect(url_for("index"))
    finally:
        if os.path.exists(input_path):
            os.remove(input_path)

    return render_template_string(
        PAGE, download_url=url_for("download", filename=output_filename)
    )


@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(OUTPUT_DIR, filename)
    return send_file(path, as_attachment=True)


if __name__ == "__main__":
    # host="0.0.0.0" makes it reachable from other devices on your Wi-Fi, not just this laptop
    app.run(host="0.0.0.0", port=5000, debug=False)
