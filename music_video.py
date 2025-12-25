import streamlit as st
import tempfile
import os

import moviepy
import decorator
import imageio_ffmpeg

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip
)
from PIL import Image  # Add this import

# ---------- PAGE ----------
st.set_page_config(page_title="Simple Video Maker", layout="centered")
st.title("🎬 Simple Video Maker")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
MoviePy        : {moviepy.__version__}
Decorator      : {decorator.__version__}
FFmpeg (path)  : {imageio_ffmpeg.get_ffmpeg_exe()}
""")

# ---------- UPLOADS ----------
bg_file = st.file_uploader(
    "Background (Video or Audio)",
    type=["mp4", "mov", "avi", "mp3", "wav"]
)

overlay_file = st.file_uploader(
    "Overlay (Image or Video)",
    type=["mp4", "mov", "avi", "png", "jpg", "jpeg"]
)

# ---------- PROCESS ----------
if st.button("Create Video") and bg_file and overlay_file:

    with st.spinner("Processing video..."):

        def save_temp(upload):
            f = tempfile.NamedTemporaryFile(delete=False)
            f.write(upload.read())
            f.close()
            return f.name

        bg_path = save_temp(bg_file)
        ov_path = save_temp(overlay_file)

        TARGET_FPS = 24
        WIDTH, HEIGHT = 1280, 720

        # ----- BACKGROUND -----
        if bg_file.type.startswith("video"):
            bg = VideoFileClip(bg_path).set_fps(TARGET_FPS)
        else:
            audio = AudioFileClip(bg_path)
            bg = (
                ColorClip((WIDTH, HEIGHT), color=(0, 0, 0), duration=audio.duration)
                .set_audio(audio)
                .set_fps(TARGET_FPS)
            )

        # ----- OVERLAY -----
        if overlay_file.type.startswith("image"):
            ov = (
                ImageClip(ov_path)
                .set_duration(bg.duration)
                .resize(height=400)
                .set_position("center")
                .set_fps(TARGET_FPS)
            )
        else:
            ov = (
                VideoFileClip(ov_path)
                .resize(height=400)
                .set_position("center")
                .set_fps(TARGET_FPS)
            )

            if ov.duration > bg.duration:
                ov = ov.subclip(0, bg.duration)

        # ----- FINAL -----
        final = CompositeVideoClip(
            [bg, ov],
            size=(WIDTH, HEIGHT)
        ).set_fps(TARGET_FPS)

        output = os.path.join(tempfile.gettempdir(), "final_video.mp4")

        final.write_videofile(
            output,
            codec="libx264",
            audio_codec="aac",
            fps=TARGET_FPS,
            threads=2
        )

    st.success("✅ Video created successfully")

    with open(output, "rb") as f:
        st.download_button(
            "⬇ Download video",
            f,
            file_name="final_video.mp4",
            mime="video/mp4"
        )
