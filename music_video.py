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
VERSION = "2.2.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Fullscreen Video Maker", layout="centered")
st.title(f"📱 Fullscreen Video Maker v{VERSION}")
st.markdown("Create fullscreen videos with background audio")

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
        help="Upload ANY file - only audio will be used"
    )

with col2:
    overlay_file = st.file_uploader(
        "Fullscreen Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif", "webp", "bmp"],
        help="Upload image/video - will fill entire screen"
    )

# ---------- MOBILE SCREEN SETTINGS ----------
st.sidebar.subheader("📱 Screen Settings")
screen_option = st.sidebar.selectbox(
    "Screen Size",
    ["Instagram Reels (1080x1920)", "TikTok (1080x1920)", "YouTube Shorts (1080x1920)", 
     "Instagram Square (1080x1080)", "Custom Size"]
)

if screen_option == "Instagram Reels (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "TikTok (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "YouTube Shorts (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "Instagram Square (1080x1080)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1080
else:
    SCREEN_WIDTH = st.sidebar.number_input("Width", min_value=480, max_value=3840, value=1080)
    SCREEN_HEIGHT = st.sidebar.number_input("Height", min_value=480, max_value=3840, value=1920)

st.sidebar.info(f"Screen: {SCREEN_WIDTH} × {SCREEN_HEIGHT}")

# ---------- OVERLAY FIT OPTIONS ----------
st.sidebar.subheader("🎨 Fit Options")
fit_option = st.sidebar.radio(
    "How to fit overlay on screen",
    ["Fill Screen (Crop if needed)", "Fit Entire (Keep all content)", "Stretch to Fit"]
)

# ---------- PROCESS ----------
if st.button("🎬 Create Fullscreen Video", type="primary") and background_file and overlay_file:

    with st.spinner("Creating your fullscreen video..."):
        
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
            st.info("🎵 Extracting audio...")
            
            # Check if background is video
            is_video = background_file.type.startswith('video') or bg_ext in ['.mp4', '.mov', '.avi', '.mpeg', '.mkv']
            
            if is_video:
                video_clip = VideoFileClip(bg_path)
                audio_clip = video_clip.audio
                if audio_clip is None:
                    st.error("❌ No audio found!")
                    st.stop()
            else:
                audio_clip = AudioFileClip(bg_path)
            
            audio_duration = audio_clip.duration
            st.info(f"Audio: {audio_duration:.1f} seconds")
            
            # ----- STEP 2: PROCESS OVERLAY TO FIT SCREEN -----
            st.info("🖼️ Processing overlay for fullscreen...")
            
            # Check if overlay is image
            is_image = overlay_file.type.startswith('image') or overlay_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
            
            if is_image:
                # Open image
                img = Image.open(overlay_path)
                img_width, img_height = img.size
                st.info(f"Original image: {img_width} × {img_height}")
                
                # Calculate scaling based on fit option
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                image_ratio = img_width / img_height
                
                if fit_option == "Fill Screen (Crop if needed)":
                    # Crop to fill screen completely
                    if image_ratio > screen_ratio:
                        # Image is wider than screen - crop sides
                        new_height = img_height
                        new_width = int(img_height * screen_ratio)
                        left = (img_width - new_width) // 2
                        top = 0
                        right = left + new_width
                        bottom = img_height
                    else:
                        # Image is taller than screen - crop top/bottom
                        new_width = img_width
                        new_height = int(img_width / screen_ratio)
                        left = 0
                        top = (img_height - new_height) // 2
                        right = img_width
                        bottom = top + new_height
                    
                    # Crop image
                    img = img.crop((left, top, right, bottom))
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    # Fit entire image within screen (black bars)
                    if image_ratio > screen_ratio:
                        # Image is wider - fit to width
                        new_width = SCREEN_WIDTH
                        new_height = int(SCREEN_WIDTH / image_ratio)
                    else:
                        # Image is taller - fit to height
                        new_height = SCREEN_HEIGHT
                        new_width = int(SCREEN_HEIGHT * image_ratio)
                    
                    img = img.resize((new_width, new_height), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                    
                    # Create new image with black background
                    background = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
                    # Paste centered
                    paste_x = (SCREEN_WIDTH - new_width) // 2
                    paste_y = (SCREEN_HEIGHT - new_height) // 2
                    background.paste(img, (paste_x, paste_y))
                    img = background
                    
                else:  # "Stretch to Fit"
                    # Stretch image to fill screen (distorts if aspect ratio differs)
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                
                # Save processed image
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                img.save(temp_img.name, "PNG", quality=95)
                
                # Create image clip
                overlay = ImageClip(temp_img.name, duration=audio_duration)
                
            else:
                # VIDEO OVERLAY
                overlay = VideoFileClip(overlay_path)
                orig_width, orig_height = overlay.size
                st.info(f"Original video: {orig_width} × {orig_height}, {overlay.duration:.1f}s")
                
                # Handle duration
                if overlay.duration < audio_duration:
                    # Loop video
                    loops = int(audio_duration // overlay.duration) + 1
                    overlay = concatenate_videoclips([overlay] * loops)
                    overlay = overlay.subclip(0, audio_duration)
                elif overlay.duration > audio_duration:
                    overlay = overlay.subclip(0, audio_duration)
                
                # Resize video based on fit option
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                video_ratio = orig_width / orig_height
                
                if fit_option == "Fill Screen (Crop if needed)":
                    # Crop to fill
                    if video_ratio > screen_ratio:
                        # Video wider than screen - crop sides
                        crop_width = int(orig_height * screen_ratio)
                        x_center = orig_width // 2
                        overlay = overlay.crop(x1=x_center - crop_width//2, x2=x_center + crop_width//2)
                    else:
                        # Video taller than screen - crop top/bottom
                        crop_height = int(orig_width / screen_ratio)
                        y_center = orig_height // 2
                        overlay = overlay.crop(y1=y_center - crop_height//2, y2=y_center + crop_height//2)
                    
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    # Fit with black bars
                    if video_ratio > screen_ratio:
                        # Fit to width
                        overlay = overlay.resize(width=SCREEN_WIDTH)
                    else:
                        # Fit to height
                        overlay = overlay.resize(height=SCREEN_HEIGHT)
                    
                    # Create black background
                    background = ColorClip((SCREEN_WIDTH, SCREEN_HEIGHT), color=(0, 0, 0), duration=overlay.duration)
                    # Position overlay
                    overlay = overlay.set_position('center')
                    overlay = CompositeVideoClip([background, overlay], size=(SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                else:  # "Stretch to Fit"
                    # Stretch video
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
            
            # ----- STEP 3: ADD AUDIO TO OVERLAY -----
            st.info("🎥 Adding audio...")
            
            # If overlay is already a CompositeVideoClip (from fit entire), extract the actual overlay
            if isinstance(overlay, CompositeVideoClip):
                # Get the actual video from composite
                overlay_with_audio = overlay.set_audio(audio_clip)
                final_video = overlay_with_audio
            else:
                # Regular overlay
                overlay = overlay.set_audio(audio_clip)
                final_video = overlay
            
            final_video = final_video.set_duration(audio_duration)
            final_video = final_video.set_fps(FPS)
            
            # ----- STEP 4: SAVE VIDEO -----
            st.info("💾 Saving video...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Optimize for mobile
            final_video.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                bitrate="10M",  # Higher bitrate for quality
                verbose=False,
                logger=None,
                threads=2,
                preset='medium',
                ffmpeg_params=['-movflags', '+faststart']  # For mobile playback
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
            
            st.success(f"✅ Fullscreen video created!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 5: SHOW RESULT -----
    st.subheader("📱 Your Fullscreen Video")
    
    # Show preview in phone frame
    preview_width = min(400, SCREEN_WIDTH)
    preview_height = int(preview_width * (SCREEN_HEIGHT / SCREEN_WIDTH))
    
    phone_frame_html = f"""
    <div style="
        width: {preview_width}px;
        height: {preview_height}px;
        margin: 20px auto;
        border: 12px solid #222;
        border-radius: 40px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        background: black;
        position: relative;
    ">
    <div style="
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 6px;
        background: #333;
        border-radius: 0 0 10px 10px;
    "></div>
    """
    st.markdown(phone_frame_html, unsafe_allow_html=True)
    
    # Video preview
    try:
        st.video(output_path)
    except:
        st.info("💡 Preview below - download for full quality")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Video info
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.metric("Duration", f"{audio_duration:.1f}s")
        st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
    with col_info2:
        st.metric("Fit Mode", fit_option)
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        st.metric("File Size", f"{file_size:.1f} MB")
    
    # Download
    with open(output_path, "rb") as f:
        st.download_button(
            f"⬇ Download Fullscreen Video ({file_size:.1f} MB)",
            f,
            file_name=f"fullscreen_{SCREEN_WIDTH}x{SCREEN_HEIGHT}.mp4",
            mime="video/mp4",
            type="primary"
        )

else:
    # Show instructions
    st.markdown("""
    ## 📱 Create Fullscreen Mobile Videos
    
    ### How it works:
    1. **Upload Background** - Any audio/video file (only audio used)
    2. **Upload Overlay** - Image or video (will fill entire screen)
    3. **Choose Fit Option** - How overlay fits on screen
    4. **Click Create** - Get fullscreen mobile video
    
    ### 🎨 Fit Options Explained:
    - **Fill Screen** - Crops edges to fill screen completely
    - **Fit Entire** - Shows entire content (black bars if needed)
    - **Stretch to Fit** - Stretches to fill (may distort)
    
    ### 📱 Perfect for:
    - Instagram Reels/TikTok
    - YouTube Shorts
    - Instagram Stories
    - Mobile wallpaper videos
    """)

# ---------- FIT OPTION VISUAL GUIDE ----------
with st.expander("🎯 Visual Guide to Fit Options"):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### **Fill Screen**")
        st.markdown("""
        ```
        ┌───────────┐
        │███████████│
        │████ IMG ██│ ← Crops edges
        │███████████│
        └───────────┘
        ```
        - Crops image if needed
        - No empty space
        - Best for social media
        """)
    
    with col2:
        st.markdown("### **Fit Entire**")
        st.markdown("""
        ```
        ┌───────────┐
        │░░░░░░░░░░░│
        │░░░ IMG ░░░│ ← Shows all content
        │░░░░░░░░░░░│
        └───────────┘
        ```
        - Shows everything
        - May have black bars
        - Good for photos
        """)
    
    with col3:
        st.markdown("### **Stretch to Fit**")
        st.markdown("""
        ```
        ┌───────────┐
        │┌─┬─────┬─┐│
        ││ │     │ ││ ← Stretches image
        │└─┴─────┴─┘│
        └───────────┘
        ```
        - Fills screen completely
        - May distort image
        - Use with caution
        """)

# Cleanup output after 10 minutes
@st.cache_resource(ttl=600)
def cleanup_output():
    if 'output_path' in locals() and os.path.exists(output_path):
        try:
            os.remove(output_path)
        except:
            pass
