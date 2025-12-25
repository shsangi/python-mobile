import streamlit as st
import tempfile
import os
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
VERSION = "2.1.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Music Video Maker", layout="centered")
st.title(f"🎵 Music Video Maker v{VERSION}")
st.markdown("Create videos with audio from any file and image/video overlay")

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
    background_file = st.file_uploader(
        "Background Music/Video",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi", "mpeg", "mkv"],
        help="Upload ANY file (video or audio) - only the audio will be used"
    )

with col2:
    overlay_file = st.file_uploader(
        "Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif", "webp"],
        help="Upload image or video to display on screen"
    )

# ---------- SIMPLE PROCESS ----------
if st.button("🎬 Create Music Video", type="primary") and background_file and overlay_file:

    with st.spinner("Creating your music video..."):
        
        # Save uploaded files
        def save_temp(upload, suffix=""):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            f.write(upload.read())
            f.close()
            return f.name
        
        # Get file extension
        bg_ext = os.path.splitext(background_file.name)[1].lower()
        overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
        
        # Save files with proper extensions
        bg_path = save_temp(background_file, bg_ext)
        overlay_path = save_temp(overlay_file, overlay_ext)
        
        # Video settings
        VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1920  # Vertical mobile format
        FPS = 30
        
        try:
            # ----- STEP 1: EXTRACT AUDIO FROM BACKGROUND FILE -----
            st.info("🎵 Extracting audio...")
            
            # Check file type by extension or content type
            is_video_file = background_file.type.startswith('video') or bg_ext in ['.mp4', '.mov', '.avi', '.mpeg', '.mkv']
            
            if is_video_file:
                # If it's a video file, extract audio
                video_clip = VideoFileClip(bg_path)
                audio_clip = video_clip.audio
                if audio_clip is None:
                    st.error("❌ No audio found in the video file!")
                    st.stop()
            else:
                # If it's an audio file
                audio_clip = AudioFileClip(bg_path)
            
            audio_duration = audio_clip.duration
            st.info(f"Audio duration: {audio_duration:.1f} seconds")
            
            # ----- STEP 2: CREATE SIMPLE BACKGROUND -----
            st.info("🎨 Creating background...")
            # Create a simple gradient-like background (dark to darker)
            background = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=(15, 15, 25),  # Dark blue-black
                duration=audio_duration
            )
            
            # ----- STEP 3: PROCESS OVERLAY -----
            st.info("🖼️ Processing overlay...")
            
            # Check if overlay is image or video
            is_image = overlay_file.type.startswith('image') or overlay_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']
            
            if is_image:
                # For images
                try:
                    img = Image.open(overlay_path)
                    img_width, img_height = img.size
                    st.info(f"Image size: {img_width}x{img_height}")
                    
                    # Simple resize - make it 70% of video height
                    target_height = int(VIDEO_HEIGHT * 0.7)
                    target_width = int(img_width * (target_height / img_height))
                    
                    # Ensure not too wide
                    if target_width > VIDEO_WIDTH * 0.9:
                        target_width = int(VIDEO_WIDTH * 0.9)
                        target_height = int(img_height * (target_width / img_width))
                    
                    # Resize
                    if hasattr(Image, 'Resampling'):
                        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    else:
                        img = img.resize((target_width, target_height), Image.LANCZOS)
                    
                    # Save resized
                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    img.save(temp_img.name, "PNG")
                    
                    # Create image clip
                    overlay = ImageClip(temp_img.name, duration=audio_duration)
                    
                except Exception as e:
                    st.warning(f"Image issue: {e}")
                    # Fallback - use original
                    overlay = ImageClip(overlay_path, duration=audio_duration)
                    
            else:
                # For video overlays
                try:
                    overlay = VideoFileClip(overlay_path)
                    st.info(f"Video overlay: {overlay.size[0]}x{overlay.size[1]}, {overlay.duration:.1f}s")
                    
                    # Handle duration
                    if overlay.duration < audio_duration:
                        # Loop video
                        loops = int(audio_duration // overlay.duration) + 1
                        overlay = concatenate_videoclips([overlay] * loops)
                        overlay = overlay.subclip(0, audio_duration)
                    elif overlay.duration > audio_duration:
                        # Trim video
                        overlay = overlay.subclip(0, audio_duration)
                    
                    # Simple resize
                    try:
                        overlay = overlay.resize(height=int(VIDEO_HEIGHT * 0.7))
                    except:
                        pass  # Skip resize if it fails
                    
                except Exception as e:
                    st.error(f"Video overlay error: {e}")
                    # Create placeholder
                    overlay = ColorClip(
                        size=(500, 500),
                        color=(200, 100, 100),
                        duration=audio_duration
                    )
            
            # Position overlay
            overlay = overlay.set_position("center")
            
            # ----- STEP 4: COMBINE EVERYTHING -----
            st.info("🎥 Creating final video...")
            
            # Create composite
            final_video = CompositeVideoClip(
                [background, overlay],
                size=(VIDEO_WIDTH, VIDEO_HEIGHT)
            )
            
            # Add audio
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(audio_duration)
            final_video = final_video.set_fps(FPS)
            
            # ----- STEP 5: SAVE VIDEO -----
            st.info("💾 Saving video file...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Simple write
            final_video.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None,
                threads=2,
                preset='fast'
            )
            
            # Cleanup
            cleanup_files = [bg_path, overlay_path]
            if 'temp_img' in locals():
                cleanup_files.append(temp_img.name)
            
            for file in cleanup_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                    except:
                        pass
            
            st.success(f"✅ Music video created successfully!")
            
        except Exception as e:
            st.error(f"❌ Error creating video: {str(e)}")
            import traceback
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 6: SHOW RESULT -----
    st.subheader("🎬 Your Music Video")
    
    # Video info
    video_info = f"""
    **Video Info:**
    - Duration: {audio_duration:.1f} seconds
    - Resolution: {VIDEO_WIDTH} × {VIDEO_HEIGHT} (Vertical)
    - Background: Audio from {background_file.name}
    - Overlay: {overlay_file.name}
    """
    st.markdown(video_info)
    
    # Preview
    try:
        st.video(output_path)
    except:
        st.info("💡 *Preview may not show in browser. Download to view.*")
    
    # Download
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
        
        with open(output_path, "rb") as f:
            st.download_button(
                f"⬇ Download Video ({file_size:.1f} MB)",
                f,
                file_name="music_video.mp4",
                mime="video/mp4",
                type="primary"
            )
        
        # Auto-cleanup after 5 minutes
        @st.cache_resource(ttl=300)
        def cleanup_output():
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass

else:
    # Show instructions when no files uploaded
    st.markdown("""
    ### 🎯 How to use this tool:
    
    1. **Upload Background** (any of these):
       - Music file: MP3, WAV, M4A, AAC
       - Video file: MP4, MOV, AVI, MKV
       - *Only the audio will be used*
    
    2. **Upload Overlay** (any of these):
       - Image: PNG, JPG, JPEG, GIF, WEBP
       - Video: MP4, MOV, AVI
    
    3. **Click "Create Music Video"**
    
    ### ✨ What you get:
    - Vertical video (1080×1920)
    - Your audio playing
    - Your overlay displayed
    - MP4 format ready to share
    """)

# ---------- FEATURES ----------
with st.expander("✨ Features"):
    st.markdown("""
    ### ✅ What this tool does:
    
    **Background Audio:**
    - Accepts ANY audio or video file
    - Extracts audio automatically
    - Uses only the audio track
    
    **Overlay Display:**
    - Images: Displayed for full duration
    - Videos: Looped if shorter than audio
    - Auto-resized to fit screen
    
    **Output:**
    - Vertical format (mobile-friendly)
    - High quality MP4
    - Fast processing
    - Clean, simple interface
    """)

# ---------- TROUBLESHOOTING ----------
with st.expander("🛠️ Need help?"):
    st.markdown("""
    ### Common issues:
    
    **File not working?**
    - Try converting to MP3 (for audio) or MP4 (for video)
    - Use online converters like CloudConvert
    
    **Video too large?**
    - Trim your audio/video before uploading
    - Use shorter files (<10 minutes)
    
    **Quality issues?**
    - Use high-quality source files
    - Images: 1000px minimum width/height
    
    **Slow processing?**
    - Smaller files process faster
    - Close other browser tabs
    """)
