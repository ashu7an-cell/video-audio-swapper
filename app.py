import math
import os
import tempfile

import streamlit as st
from moviepy import VideoFileClip, AudioFileClip, concatenate_audioclips

# Background audio file must sit next to this script in the repo
AUDIO_PATH = "background_audio.mp3"

st.set_page_config(page_title="Video Audio Swapper", page_icon="🎬")
st.title("🎬 Video Audio Swapper")
st.write("Upload a video and get it back with the background track added.")


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


if not os.path.isfile(AUDIO_PATH):
    st.error(f"Background audio file not found in the app folder: {AUDIO_PATH}")
    st.stop()

uploaded_file = st.file_uploader("Choose a video", type=["mp4", "mov", "mkv", "avi", "webm"])

if uploaded_file is not None:
    if st.button("Process Video"):
        with st.spinner("Processing... this can take a minute for longer videos."):
            with tempfile.TemporaryDirectory() as tmp_dir:
                ext = os.path.splitext(uploaded_file.name)[1] or ".mp4"
                input_path = os.path.join(tmp_dir, f"input{ext}")
                output_path = os.path.join(tmp_dir, f"output{ext}")

                with open(input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    process_video(input_path, output_path)
                    with open(output_path, "rb") as f:
                        result_bytes = f.read()

                    st.success("Done!")
                    st.download_button(
                        label="Download processed video",
                        data=result_bytes,
                        file_name=f"{os.path.splitext(uploaded_file.name)[0]}_with_audio{ext}",
                        mime="video/mp4",
                    )
                except Exception as e:
                    st.error(f"Processing failed: {e}")
