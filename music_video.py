import streamlit as st
import tempfile
import os
import numpy as np

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
from PIL import Image
import moviepy.video.fx.resize as resize_module

# ---------- PATCH MOVIEPY RESIZE FUNCTION ----------
# Monkey-patch the resizer function in moviepy to use LANCZOS instead of ANTIALIAS
def patched_resizer(picture, newsize):
    """Resizes the picture using PIL."""
    h, w = picture.shape[:2]
    
    # Convert numpy array to PIL Image
    pilim = Image.fromarray(picture)
    
    # Use LANCZOS instead of ANTIALIAS
    if hasattr(Image, 'Resampling'):  # Pillow 9.1.0+
        resample_method = Image.Resampling.LANCZOS
    elif hasattr(Image, 'LANCZOS'):  # Pillow < 9.1.0
        resample_method = Image.LANCZOS
    else:  # Fallback
        resample_method = Image.ANTIALIAS
    
    resized_pil = pilim.resize(newsize[::-1], resample_method)
    
    # Convert back to numpy array
    return np.array(resized_pil)

# Apply the patch
resize_module.resizer = patched_resizer

# ---------- PAGE ----------
st.set_page_config(page_title="Simple Video Maker", layout="centered")
st.title("🎬 Simple Video Maker")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
MoviePy        : {moviepy.__version__}
Decorator      : {decorator.__version__}
FFmpeg (path)  : {imageio_ffmpeg.get_ffmpeg_exe()}
Pillow         : {Image.__version__}
""")

# ---------- UPLOADS ----------
bg_file = st.file_uploader(
    "Background (Video or Audio)",
    type=["mp4", "mov", "avi", "mp3", "wav", "mpeg4"]
)

overlay_file = st.file_uploader(
    "Overlay (Image or Video)",
    type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "mpeg4"]
)

# ---------- PROCESS ----------
if st.button("Create Video") and bg_file and overlay_file:

    with st.spinner("Processing video..."):
        # Create temp files
        def save_temp(upload):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.name)[1])
            f.write(upload.read())
            f.close()
            return f.name

        bg_path = save_temp(bg_file)
        ov_path = save_temp(overlay_file)

        TARGET_FPS = 24
        WIDTH, HEIGHT = 1280, 720

        try:
            # ----- BACKGROUND -----
            if bg_file.type.startswith("video"):
                bg = VideoFileClip(bg_path)
                bg = bg.set_fps(TARGET_FPS)
                # If background video is too short, loop it
                if bg.duration < 5:  # Arbitrary minimum
                    bg = bg.loop(duration=10)  # Loop to 10 seconds
            else:
                audio = AudioFileClip(bg_path)
                bg = ColorClip(
                    (WIDTH, HEIGHT), 
                    color=(0, 0, 0), 
                    duration=audio.duration
                )
                bg = bg.set_audio(audio).set_fps(TARGET_FPS)

            # ----- OVERLAY -----
            if overlay_file.type.startswith("image"):
                # Load and resize image manually
                pil_img = Image.open(ov_path)
                original_width, original_height = pil_img.size
                
                # Calculate new size maintaining aspect ratio
                new_height = 400
                new_width = int(original_width * (new_height / original_height))
                
                # Resize using modern Pillow method
                if hasattr(Image, 'Resampling'):
                    resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                else:
                    resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                
                # Save resized image to temp file
                temp_img_path = os.path.join(tempfile.gettempdir(), "resized_overlay.png")
                resized_img.save(temp_img_path, format="PNG")
                
                # Create ImageClip from resized image
                ov = ImageClip(temp_img_path).set_duration(bg.duration)
                
            else:
                ov = VideoFileClip(ov_path)
                # Resize overlay
                ov = ov.resize(height=400)
                
                # Match duration with background
                if ov.duration > bg.duration:
                    ov = ov.subclip(0, bg.duration)
                elif ov.duration < bg.duration:
                    # Loop video overlay if it's shorter than background
                    ov = ov.loop(duration=bg.duration)
            
            # Position overlay in center
            ov = ov.set_position(("center", "center")).set_fps(TARGET_FPS)
            
            # Ensure both clips have the same duration
            min_duration = min(bg.duration, ov.duration)
            bg = bg.subclip(0, min_duration)
            ov = ov.subclip(0, min_duration)

            # ----- FINAL -----
            final = CompositeVideoClip(
                [bg, ov],
                size=(WIDTH, HEIGHT)
            ).set_fps(TARGET_FPS)

            output = os.path.join(tempfile.gettempdir(), "final_video.mp4")
            
            # Write video file with error handling
            final.write_videofile(
                output,
                codec="libx264",
                audio_codec="aac",
                fps=TARGET_FPS,
                threads=2,
                logger=None  # Suppress verbose output
            )
            
            # Clean up temp image file if it exists
            if 'temp_img_path' in locals() and os.path.exists(temp_img_path):
                os.remove(temp_img_path)
                
        except Exception as e:
            st.error(f"❌ Error creating video: {str(e)}")
            st.info("Tip: Try using different file formats or smaller files.")
            st.stop()
        finally:
            # Clean up uploaded temp files
            for path in [bg_path, ov_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

    st.success("✅ Video created successfully")
    
    # Show video preview
    st.video(output)
    
    # Download button
    with open(output, "rb") as f:
        st.download_button(
            "⬇ Download Video",
            f,
            file_name="final_video.mp4",
            mime="video/mp4"
        )
    
    # Clean up final output file after session
    @st.cache_resource(ttl=300)  # Cache for 5 minutes
    def cleanup_output():
        if os.path.exists(output):
            try:
                os.remove(output)
            except:
                pass

# Optional: Add instructions
with st.expander("ℹ️ How to use"):
    st.markdown("""
    1. **Upload Background**: Choose a video or audio file
    2. **Upload Overlay**: Choose an image or video to overlay
    3. **Click "Create Video"**: The overlay will be resized and centered
    4. **Download**: Save your final video
    
    **Tips:**
    - For best results, use MP4 files
    - Overlay videos should be shorter than background
    - Images will be automatically resized to 400px height
    """)
