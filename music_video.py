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
    ColorClip,
    concatenate_videoclips
)

# Add version tracking
VERSION = "2.0.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Music Video Maker", layout="centered")
st.title(f"🎵 Music Video Maker v{VERSION}")
st.markdown("Create videos with audio background and image/video overlay")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
App Version     : {VERSION}
MoviePy        : {moviepy.__version__}
Pillow         : {Image.__version__}
""")

# ---------- UPLOADS ----------
col1, col2 = st.columns(2)

with col1:
    bg_audio = st.file_uploader(
        "Background Music",
        type=["mp3", "wav", "m4a", "aac"],
        help="Upload audio file (music, podcast, etc.)"
    )

with col2:
    overlay_file = st.file_uploader(
        "Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif"],
        help="Upload image or video to display"
    )

# ---------- SIMPLE PROCESS ----------
if st.button("🎬 Create Music Video", type="primary") and bg_audio and overlay_file:

    with st.spinner("Creating your music video..."):
        
        # Save uploaded files
        def save_temp(upload):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.name)[1])
            f.write(upload.read())
            f.close()
            return f.name
        
        audio_path = save_temp(bg_audio)
        overlay_path = save_temp(overlay_file)
        
        # Video settings
        VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1920  # Vertical mobile format
        FPS = 30
        
        try:
            # ----- STEP 1: LOAD AUDIO -----
            st.info("🎵 Loading audio...")
            audio_clip = AudioFileClip(audio_path)
            audio_duration = audio_clip.duration
            
            # ----- STEP 2: CREATE BACKGROUND (Plain color) -----
            st.info("🎨 Creating background...")
            # Create a simple colored background
            background = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=(20, 20, 30),  # Dark blue-gray
                duration=audio_duration
            )
            
            # ----- STEP 3: PROCESS OVERLAY -----
            st.info("🖼️ Processing overlay...")
            
            if overlay_file.type.startswith("image"):
                # For images: display for entire audio duration
                try:
                    # Load and resize image
                    img = Image.open(overlay_path)
                    img_width, img_height = img.size
                    
                    # Resize to fit in video (max 80% of video height)
                    max_height = int(VIDEO_HEIGHT * 0.8)
                    if img_height > max_height:
                        scale_factor = max_height / img_height
                        new_width = int(img_width * scale_factor)
                        new_height = max_height
                    else:
                        new_width = img_width
                        new_height = img_height
                    
                    # Ensure not too wide
                    if new_width > VIDEO_WIDTH * 0.9:
                        scale_factor = (VIDEO_WIDTH * 0.9) / new_width
                        new_width = int(new_width * scale_factor)
                        new_height = int(new_height * scale_factor)
                    
                    # Resize image
                    if hasattr(Image, 'Resampling'):
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Save resized image
                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    img.save(temp_img.name, "PNG")
                    
                    # Create image clip
                    overlay = ImageClip(temp_img.name, duration=audio_duration)
                    
                except Exception as e:
                    st.warning(f"Image processing issue: {e}. Using original image.")
                    overlay = ImageClip(overlay_path, duration=audio_duration)
                    
            else:
                # For videos
                try:
                    overlay = VideoFileClip(overlay_path)
                    
                    # Loop video if shorter than audio
                    if overlay.duration < audio_duration:
                        # Calculate how many times to loop
                        loops_needed = int(np.ceil(audio_duration / overlay.duration))
                        overlay = concatenate_videoclips([overlay] * loops_needed)
                        overlay = overlay.subclip(0, audio_duration)
                    elif overlay.duration > audio_duration:
                        # Trim if longer
                        overlay = overlay.subclip(0, audio_duration)
                        
                except Exception as e:
                    st.warning(f"Video processing issue: {e}")
                    # Fallback: use a placeholder
                    overlay = ColorClip(
                        size=(500, 500),
                        color=(100, 100, 200),
                        duration=audio_duration
                    )
            
            # Resize overlay to fit
            try:
                # Simple resize to 70% of video height
                target_height = int(VIDEO_HEIGHT * 0.7)
                overlay = overlay.resize(height=target_height)
            except:
                # If resize fails, try alternative method
                try:
                    overlay = overlay.resize(lambda t: 0.7)  # Scale to 70%
                except:
                    pass  # Use original size
            
            # Position overlay in center
            overlay = overlay.set_position("center")
            
            # ----- STEP 4: COMBINE EVERYTHING -----
            st.info("🎥 Combining audio and video...")
            
            # Create final video
            final_video = CompositeVideoClip(
                [background, overlay],
                size=(VIDEO_WIDTH, VIDEO_HEIGHT)
            )
            
            # Add audio
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(audio_duration)
            final_video = final_video.set_fps(FPS)
            
            # ----- STEP 5: SAVE VIDEO -----
            st.info("💾 Saving video...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Simple write with minimal options
            final_video.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None,
                threads=2
            )
            
            # Cleanup temp files
            temp_files = [audio_path, overlay_path]
            if 'temp_img' in locals():
                temp_files.append(temp_img.name)
            
            for file_path in temp_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            st.success(f"✅ Music video created! Duration: {audio_duration:.1f} seconds")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            st.stop()
    
    # ----- STEP 6: SHOW RESULT -----
    st.subheader("🎬 Your Music Video")
    
    # Show video
    try:
        st.video(output_path)
    except:
        st.info("Video preview may not show in Streamlit. Download to view.")
    
    # Download button
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    
    with open(output_path, "rb") as f:
        st.download_button(
            f"⬇ Download Video ({file_size:.1f} MB)",
            f,
            file_name="music_video.mp4",
            mime="video/mp4",
            type="primary"
        )
    
    # Cleanup output file after download
    @st.cache_resource
    def cleanup_output():
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
    
    # Show summary
    with st.expander("📊 Video Info"):
        st.write(f"- **Duration**: {audio_duration:.1f} seconds")
        st.write(f"- **Resolution**: {VIDEO_WIDTH} x {VIDEO_HEIGHT}")
        st.write(f"- **FPS**: {FPS}")
        st.write(f"- **File Size**: {file_size:.1f} MB")
        st.write(f"- **Background**: Audio only (no video)")
        st.write(f"- **Overlay**: {overlay_file.type}")

else:
    # Show instructions
    st.markdown("""
    ### How to use:
    1. **Upload Music** - Any audio file (MP3, WAV, etc.)
    2. **Upload Overlay** - Image or video to display
    3. **Click Create** - That's it!
    
    ### What happens:
    - The audio plays in background
    - Overlay displays on screen
    - Video is vertical (mobile-friendly)
    - Output is MP4 format
    """)

# ---------- SIMPLE TIPS ----------
with st.expander("💡 Tips for best results"):
    st.markdown("""
    1. **Audio Files**:
       - Use MP3 for best compatibility
       - Keep under 10 minutes
       - File size under 50MB
    
    2. **Images**:
       - Use JPG or PNG
       - Landscape images work best
       - Resolution: 1000x1000px or higher
    
    3. **Videos**:
       - Use MP4 format
       - Shorter videos loop automatically
       - Keep under 100MB
    """)
