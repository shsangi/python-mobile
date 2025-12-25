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
VERSION = "2.3.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Mobile Video Maker", layout="centered")
st.title(f"📱 Mobile Video Maker v{VERSION}")
st.markdown("Create mobile videos that fill the entire screen")

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
        "Background Music",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi", "mpeg", "mkv"],
        help="Upload audio or video file - only audio will be used"
    )

with col2:
    overlay_file = st.file_uploader(
        "Screen Content (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif", "webp", "bmp"],
        help="Upload image or video - will fill the entire screen"
    )

# ---------- SIMPLE SETTINGS ----------
st.sidebar.subheader("⚙️ Settings")

# Screen size - only mobile vertical options
screen_size = st.sidebar.selectbox(
    "Screen Size",
    ["Fullscreen Mobile (1080x1920)", "Instagram Reels (1080x1920)", 
     "TikTok (1080x1920)", "Stories (1080x1920)"]
)

SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920  # Always vertical mobile

# Auto-detect option for mobile videos
auto_detect = st.sidebar.checkbox("Auto-detect mobile videos", value=True, 
                                  help="Automatically detect and fit mobile videos to fullscreen")

# Background color (only used if needed)
bg_color = st.sidebar.color_picker("Background Color", "#000000")

# ---------- PROCESS ----------
if st.button("🎬 Create Mobile Video", type="primary", use_container_width=True) and background_file and overlay_file:

    with st.spinner("Creating your mobile video..."):
        
        # Save uploaded files
        def save_temp(upload, suffix=""):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            f.write(upload.read())
            f.close()
            return f.name
        
        # Get file extensions
        bg_ext = os.path.splitext(background_file.name)[1].lower()
        overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
        
        # Save files
        bg_path = save_temp(background_file, bg_ext)
        overlay_path = save_temp(overlay_file, overlay_ext)
        
        FPS = 30
        
        try:
            # ----- STEP 1: EXTRACT AUDIO -----
            st.info("🎵 Processing audio...")
            
            # Check if background is video
            is_video = background_file.type.startswith('video') or bg_ext in ['.mp4', '.mov', '.avi', '.mpeg', '.mkv']
            
            if is_video:
                video_clip = VideoFileClip(bg_path)
                audio_clip = video_clip.audio
                if audio_clip is None:
                    st.error("❌ No audio found in the video!")
                    st.stop()
                video_clip.close()  # Close to free resources
            else:
                audio_clip = AudioFileClip(bg_path)
            
            audio_duration = audio_clip.duration
            st.info(f"Audio duration: {audio_duration:.1f} seconds")
            
            # ----- STEP 2: PROCESS OVERLAY TO FILL SCREEN -----
            st.info("🖼️ Preparing screen content...")
            
            # Check if overlay is image
            is_image = overlay_file.type.startswith('image') or overlay_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
            
            if is_image:
                # ----- IMAGE PROCESSING -----
                img = Image.open(overlay_path)
                img_width, img_height = img.size
                img_ratio = img_width / img_height
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                
                st.info(f"Image: {img_width}×{img_height} (ratio: {img_ratio:.2f})")
                
                # Decide how to fit based on aspect ratio
                if auto_detect and abs(img_ratio - screen_ratio) < 0.1:
                    # Image is already mobile aspect ratio - fill screen
                    st.info("📱 Image is mobile aspect - filling screen")
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                else:
                    # Image is not mobile aspect - crop to fill
                    st.info("✂️ Cropping to fill screen")
                    if img_ratio > screen_ratio:
                        # Image is wider than screen - crop sides
                        new_height = img_height
                        new_width = int(img_height * screen_ratio)
                        left = (img_width - new_width) // 2
                        img = img.crop((left, 0, left + new_width, new_height))
                    else:
                        # Image is taller than screen - crop top/bottom
                        new_width = img_width
                        new_height = int(img_width / screen_ratio)
                        top = (img_height - new_height) // 2
                        img = img.crop((0, top, new_width, top + new_height))
                    
                    # Resize to screen size
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                
                # Save image
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                img.save(temp_img.name, "PNG", quality=95)
                
                # Create image clip
                overlay = ImageClip(temp_img.name, duration=audio_duration)
                
            else:
                # ----- VIDEO PROCESSING -----
                overlay = VideoFileClip(overlay_path)
                orig_width, orig_height = overlay.size
                video_ratio = orig_width / orig_height
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                
                st.info(f"Video: {orig_width}×{orig_height} (ratio: {video_ratio:.2f}), {overlay.duration:.1f}s")
                
                # Handle duration
                if overlay.duration < audio_duration:
                    st.info("🔄 Looping video to match audio duration")
                    loops = int(audio_duration // overlay.duration) + 1
                    overlay = concatenate_videoclips([overlay] * loops)
                    overlay = overlay.subclip(0, audio_duration)
                elif overlay.duration > audio_duration:
                    st.info("✂️ Trimming video to match audio duration")
                    overlay = overlay.subclip(0, audio_duration)
                
                # Check if video is already mobile aspect ratio
                if auto_detect and abs(video_ratio - screen_ratio) < 0.1:
                    # Video is already mobile aspect - use as is
                    st.info("📱 Video is mobile aspect - using fullscreen")
                    if (orig_width, orig_height) != (SCREEN_WIDTH, SCREEN_HEIGHT):
                        overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
                else:
                    # Video needs cropping to fill screen
                    st.info("🎬 Cropping video to fill screen")
                    
                    if video_ratio > screen_ratio:
                        # Video is wider than screen - crop sides
                        crop_width = int(orig_height * screen_ratio)
                        x_center = orig_width // 2
                        overlay = overlay.crop(x1=x_center - crop_width//2, 
                                              x2=x_center + crop_width//2,
                                              y1=0, y2=orig_height)
                    else:
                        # Video is taller than screen - crop top/bottom
                        crop_height = int(orig_width / screen_ratio)
                        y_center = orig_height // 2
                        overlay = overlay.crop(x1=0, x2=orig_width,
                                              y1=y_center - crop_height//2,
                                              y2=y_center + crop_height//2)
                    
                    # Resize to screen size
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
            
            # ----- STEP 3: COMBINE WITH AUDIO -----
            st.info("🎥 Finalizing video...")
            
            # Add audio to overlay
            overlay = overlay.set_audio(audio_clip)
            overlay = overlay.set_duration(audio_duration)
            overlay = overlay.set_fps(FPS)
            
            # ----- STEP 4: SAVE VIDEO -----
            st.info("💾 Saving video...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Write with mobile optimization
            overlay.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                bitrate="8M",  # Good quality for mobile
                verbose=False,
                logger=None,
                threads=2,
                preset='fast',
                ffmpeg_params=['-movflags', '+faststart']
            )
            
            # Cleanup temp files
            cleanup_files = [bg_path, overlay_path]
            if 'temp_img' in locals():
                cleanup_files.append(temp_img.name)
            
            for file in cleanup_files:
                if os.path.exists(file):
                    try:
                        os.remove(file)
                    except:
                        pass
            
            st.success(f"✅ Mobile video created successfully!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 5: SHOW RESULT -----
    st.subheader("📱 Your Mobile Video")
    
    # Create phone preview
    phone_html = """
    <div style="
        max-width: 300px;
        margin: 0 auto;
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 40px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.3);
    ">
    <div style="
        background: #111;
        border-radius: 30px;
        padding: 10px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
    ">
    """
    st.markdown(phone_html, unsafe_allow_html=True)
    
    # Video preview
    try:
        st.video(output_path)
    except:
        st.info("💡 Video preview - download for full quality")
    
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    # Video stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📏 Size", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
    with col2:
        st.metric("⏱️ Duration", f"{audio_duration:.1f}s")
    with col3:
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        st.metric("📦 File Size", f"{file_size:.1f} MB")
    
    # Download button
    with open(output_path, "rb") as f:
        st.download_button(
            "⬇ Download Mobile Video",
            f,
            file_name="mobile_video.mp4",
            mime="video/mp4",
            type="primary",
            use_container_width=True
        )
    
    # Info about the video
    with st.expander("📊 Video Details"):
        if is_image:
            st.write(f"**Image:** {overlay_file.name}")
            st.write(f"**Original:** {img_width}×{img_height}")
            st.write(f"**Processed:** {SCREEN_WIDTH}×{SCREEN_HEIGHT}")
        else:
            st.write(f"**Video:** {overlay_file.name}")
            st.write(f"**Original:** {orig_width}×{orig_height}")
            st.write(f"**Processed:** {SCREEN_WIDTH}×{SCREEN_HEIGHT}")
            st.write(f"**Duration:** {overlay.duration:.1f}s")
        st.write(f"**Audio:** {background_file.name}")
        st.write(f"**Audio Duration:** {audio_duration:.1f}s")

else:
    # Show instructions
    st.markdown("""
    ## 🎯 How to Create Mobile Videos
    
    ### Simple 3-Step Process:
    
    1. **🎵 Upload Audio**  
       Any music file (MP3, WAV) or video (MP4, MOV)  
       *Only the audio will be used*
    
    2. **📱 Upload Screen Content**  
       Image or video to display  
       *Will fill the entire mobile screen*
    
    3. **🎬 Click "Create Mobile Video"**  
       Get a vertical mobile video
    
    ### ✨ Key Features:
    - **Auto-detects mobile videos** - Fits them perfectly
    - **Fills entire screen** - No empty borders
    - **Vertical format** - Perfect for mobile
    - **High quality** - Clear video and audio
    
    ### 📱 Perfect For:
    - Instagram Reels & Stories
    - TikTok videos
    - YouTube Shorts
    - WhatsApp Status
    - Mobile presentations
    """)

# ---------- TIPS ----------
with st.expander("💡 Tips for Best Results"):
    st.markdown("""
    ### For Best Quality:
    
    **📱 Mobile Videos:**
    - Upload vertical videos (9:16 aspect ratio)
    - Use 1080x1920 or similar resolution
    - Enable "Auto-detect mobile videos" in settings
    
    **🖼️ Images:**
    - Use vertical images (taller than wide)
    - Minimum 1080x1920 pixels
    - High quality JPG or PNG
    
    **🎵 Audio:**
    - MP3 files work best
    - Keep under 5 minutes for quick processing
    - Normalize audio volume beforehand
    
    **⚡ Processing Tips:**
    - Smaller files process faster
    - Close other browser tabs
    - Use MP4 format for videos
    """)

# Auto cleanup
@st.cache_resource(ttl=300)
def cleanup():
    if 'output_path' in locals() and os.path.exists(output_path):
        try:
            os.remove(output_path)
        except:
            pass