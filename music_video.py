import streamlit as st
import tempfile
import os
import numpy as np
from PIL import Image

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

# ---------- CUSTOM RESIZE FUNCTION ----------
def resize_clip(clip, height=None, width=None):
    """
    Custom resize function that works around MoviePy's deprecated ANTIALIAS issue.
    """
    if height is None and width is None:
        return clip
    
    # Get original dimensions
    original_width, original_height = clip.size
    
    # Calculate new dimensions
    if height is not None and width is not None:
        new_width, new_height = width, height
    elif height is not None:
        new_height = height
        new_width = int(original_width * (height / original_height))
    else:  # width is not None
        new_width = width
        new_height = int(original_height * (width / original_width))
    
    # Ensure dimensions are integers
    new_width, new_height = int(new_width), int(new_height)
    
    # Create a custom transformation function
    def transform_frame(frame):
        # Convert numpy array to PIL Image
        pil_img = Image.fromarray(frame)
        
        # Use modern resampling method
        if hasattr(Image, 'Resampling'):
            resample_method = Image.Resampling.LANCZOS
        elif hasattr(Image, 'LANCZOS'):
            resample_method = Image.LANCZOS
        else:
            resample_method = Image.ANTIALIAS
        
        # Resize the image
        resized_img = pil_img.resize((new_width, new_height), resample_method)
        
        # Convert back to numpy array
        return np.array(resized_img)
    
    # Apply the transformation to the clip
    return clip.fl_image(transform_frame)

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
                # Resize background to target dimensions if needed
                if bg.size != (WIDTH, HEIGHT):
                    bg = resize_clip(bg, width=WIDTH, height=HEIGHT)
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
                
                # Ensure width is at least 1
                new_width = max(1, new_width)
                
                # Resize using modern Pillow method
                if hasattr(Image, 'Resampling'):
                    resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                elif hasattr(Image, 'LANCZOS'):
                    resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    resized_img = pil_img.resize((new_width, new_height), Image.ANTIALIAS)
                
                # Save resized image to temp file
                temp_img_path = os.path.join(tempfile.gettempdir(), "resized_overlay.png")
                resized_img.save(temp_img_path, format="PNG")
                
                # Create ImageClip from resized image
                ov = ImageClip(temp_img_path).set_duration(bg.duration)
                
            else:
                # Load video overlay
                ov = VideoFileClip(ov_path).set_fps(TARGET_FPS)
                
                # Use custom resize function instead of MoviePy's built-in resize
                ov = resize_clip(ov, height=400)
                
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
            
            # Write video file
            final.write_videofile(
                output,
                codec="libx264",
                audio_codec="aac",
                fps=TARGET_FPS,
                threads=2,
                logger=None,
                temp_audiofile=os.path.join(tempfile.gettempdir(), "temp_audio.m4a"),
                remove_temp=True
            )
            
            # Clean up temp image file if it exists
            if 'temp_img_path' in locals() and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except:
                    pass
                
        except Exception as e:
            st.error(f"❌ Error creating video: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
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
    try:
        st.video(output)
    except:
        st.info("Video preview unavailable. You can still download the file.")
    
    # Download button
    try:
        with open(output, "rb") as f:
            st.download_button(
                "⬇ Download Video",
                f,
                file_name="final_video.mp4",
                mime="video/mp4"
            )
    except Exception as e:
        st.error(f"Error preparing download: {str(e)}")

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
