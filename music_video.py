import streamlit as st
import tempfile
import os
import numpy as np
from PIL import Image
from io import BytesIO
import base64

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
VERSION = "2.3.6"  # Updated version

# ---------- PAGE ----------
st.set_page_config(page_title="Fullscreen Video Maker", layout="centered")
st.title(f"📱 Fullscreen Video Maker v{VERSION}")
st.markdown("Create fullscreen videos with background audio")

# ---------- SESSION STATE ----------
if 'bg_clip' not in st.session_state:
    st.session_state.bg_clip = None
if 'overlay_clip' not in st.session_state:
    st.session_state.overlay_clip = None
if 'bg_duration' not in st.session_state:
    st.session_state.bg_duration = 0
if 'overlay_duration' not in st.session_state:
    st.session_state.overlay_duration = 0
if 'bg_preview_path' not in st.session_state:
    st.session_state.bg_preview_path = None
if 'overlay_preview_path' not in st.session_state:
    st.session_state.overlay_preview_path = None
if 'bg_audio_clip' not in st.session_state:
    st.session_state.bg_audio_clip = None
if 'bg_path' not in st.session_state:
    st.session_state.bg_path = None
if 'overlay_path' not in st.session_state:
    st.session_state.overlay_path = None
if 'bg_is_video' not in st.session_state:
    st.session_state.bg_is_video = False
if 'overlay_is_image' not in st.session_state:
    st.session_state.overlay_is_image = False

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location and return path"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def generate_video_preview(video_path, start_time=0, end_time=None, height=200):
    """Generate preview GIF for video"""
    try:
        clip = VideoFileClip(video_path)
        
        if end_time is None or end_time > clip.duration:
            end_time = min(clip.duration, start_time + 3)
        
        # Ensure valid time range
        start_time = max(0, min(start_time, clip.duration - 0.1))
        end_time = max(start_time + 0.1, min(end_time, clip.duration))
        
        preview_clip = clip.subclip(start_time, end_time)
        
        # Convert height to integer
        height = int(height)
        preview_clip = preview_clip.resize(height=height)
        
        # Create temp file for GIF
        temp_gif = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
        temp_gif.close()
        
        preview_clip.write_gif(temp_gif.name, fps=5, program='ffmpeg')
        
        clip.close()
        preview_clip.close()
        
        return temp_gif.name
    except Exception as e:
        return None

def generate_image_preview(image_path, max_size=(300, 300)):
    """Generate preview for image"""
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size)
        
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(temp_img.name, format='PNG')
        temp_img.close()
        
        return temp_img.name
    except Exception as e:
        return None

# ---------- UPLOADS ----------
col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Music/Video",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi", "mpeg", "mkv"],
        help="Upload ANY file - only audio will be used"
    )
    
    if background_file:
        if 'prev_bg_file' not in st.session_state or st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.bg_audio_clip = None
            st.session_state.bg_preview_path = None
            st.session_state.prev_bg_file = background_file.name
        
        st.session_state.bg_path = save_uploaded_file(background_file)
        bg_ext = os.path.splitext(background_file.name)[1].lower()
        st.session_state.bg_is_video = background_file.type.startswith('video') or bg_ext in ['.mp4', '.mov', '.avi', '.mpeg', '.mkv']
        
        try:
            if st.session_state.bg_is_video:
                st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                st.session_state.bg_audio_clip = st.session_state.bg_clip.audio
                if st.session_state.bg_audio_clip is None:
                    st.error("❌ No audio found in video!")
                    st.stop()
            else:
                st.session_state.bg_clip = None
                st.session_state.bg_audio_clip = AudioFileClip(st.session_state.bg_path)
            
            st.session_state.bg_duration = st.session_state.bg_audio_clip.duration
            
            if st.session_state.bg_is_video:
                st.session_state.bg_preview_path = generate_video_preview(
                    st.session_state.bg_path, 
                    start_time=0, 
                    end_time=min(3, st.session_state.bg_duration)
                )
            
            st.success(f"✅ Loaded: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
            
        except Exception as e:
            st.error(f"Error loading background: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Fullscreen Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif", "webp", "bmp"],
        help="Upload image/video - will fill entire screen"
    )
    
    if overlay_file:
        if 'prev_overlay_file' not in st.session_state or st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.overlay_preview_path = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        st.session_state.overlay_path = save_uploaded_file(overlay_file)
        overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
        st.session_state.overlay_is_image = overlay_file.type.startswith('image') or overlay_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
        
        try:
            if st.session_state.overlay_is_image:
                st.session_state.overlay_clip = None
                st.session_state.overlay_duration = 0
                st.session_state.overlay_preview_path = generate_image_preview(st.session_state.overlay_path)
            else:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                st.session_state.overlay_preview_path = generate_video_preview(
                    st.session_state.overlay_path,
                    start_time=0,
                    end_time=min(3, st.session_state.overlay_duration)
                )
            
            st.success(f"✅ Loaded: {overlay_file.name}")
            
        except Exception as e:
            st.error(f"Error loading overlay: {str(e)}")

# ---------- DURATION SELECTION ----------
if st.session_state.bg_duration > 0:
    st.subheader("🎵 Duration Selection")
    
    audio_tab, overlay_tab = st.tabs(["🎵 Audio Settings", "🎬 Overlay Settings"])
    
    with audio_tab:
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("**Audio Duration Selector**")
            audio_start = st.slider(
                "Start Time (seconds)",
                0.0,
                st.session_state.bg_duration,
                0.0,
                0.1,
                key="audio_start",
                help="Select start point for audio"
            )
        
        with col_a2:
            st.markdown("**Audio Duration Range**")
            audio_end = st.slider(
                "End Time (seconds)",
                0.0,
                st.session_state.bg_duration,
                st.session_state.bg_duration,
                0.1,
                key="audio_end",
                help="Select end point for audio"
            )
        
        if audio_end <= audio_start:
            audio_end = min(audio_start + 1, st.session_state.bg_duration)
            st.warning(f"End time adjusted to {audio_end:.1f} seconds")
        
        audio_duration = audio_end - audio_start
        st.info(f"**Selected audio duration: {audio_duration:.1f} seconds** (from {audio_start:.1f}s to {audio_end:.1f}s)")
    
    with overlay_tab:
        if not st.session_state.overlay_is_image and st.session_state.overlay_duration > 0:
            col_o1, col_o2 = st.columns(2)
            
            with col_o1:
                st.markdown("**Overlay Start Time**")
                overlay_start = st.slider(
                    "Start Time (seconds)",
                    0.0,
                    st.session_state.overlay_duration,
                    0.0,
                    0.1,
                    key="overlay_start",
                    help="Select start point for overlay video"
                )
            
            with col_o2:
                st.markdown("**Overlay End Time**")
                overlay_end = st.slider(
                    "End Time (seconds)",
                    0.0,
                    st.session_state.overlay_duration,
                    st.session_state.overlay_duration,
                    0.1,
                    key="overlay_end",
                    help="Select end point for overlay video"
                )
            
            if overlay_end <= overlay_start:
                overlay_end = min(overlay_start + 1, st.session_state.overlay_duration)
                st.warning(f"End time adjusted to {overlay_end:.1f} seconds")
            
            overlay_selected_duration = overlay_end - overlay_start
            st.info(f"**Selected overlay duration: {overlay_selected_duration:.1f} seconds** (from {overlay_start:.1f}s to {overlay_end:.1f}s)")

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
    
    audio_start = st.session_state.get('audio_start', 0)
    audio_end = st.session_state.get('audio_end', st.session_state.bg_duration)
    overlay_start = st.session_state.get('overlay_start', 0)
    overlay_end = st.session_state.get('overlay_end', st.session_state.overlay_duration)
    
    audio_start = round(float(audio_start), 2)
    audio_end = round(float(audio_end), 2)
    overlay_start = round(float(overlay_start), 2)
    overlay_end = round(float(overlay_end), 2)
    
    SCREEN_WIDTH = int(SCREEN_WIDTH)
    SCREEN_HEIGHT = int(SCREEN_HEIGHT)
    
    with st.spinner("Creating your fullscreen video..."):
        
        try:
            # ----- STEP 1: EXTRACT AND TRIM AUDIO -----
            st.info("🎵 Extracting and trimming audio...")
            
            audio_clip = st.session_state.bg_audio_clip.subclip(audio_start, audio_end)
            audio_duration = audio_clip.duration
            st.info(f"Audio: {audio_duration:.1f} seconds (from {audio_start:.1f}s to {audio_end:.1f}s)")
            
            # ----- STEP 2: PROCESS OVERLAY -----
            st.info("🖼️ Processing overlay for fullscreen...")
            
            if st.session_state.overlay_is_image:
                # IMAGE PROCESSING
                img = Image.open(st.session_state.overlay_path)
                img_width, img_height = img.size
                st.info(f"Original image: {img_width} × {img_height}")
                
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                image_ratio = img_width / img_height
                
                if fit_option == "Fill Screen (Crop if needed)":
                    if image_ratio > screen_ratio:
                        new_height = img_height
                        new_width = int(img_height * screen_ratio)
                        left = (img_width - new_width) // 2
                        img = img.crop((left, 0, left + new_width, img_height))
                    else:
                        new_width = img_width
                        new_height = int(img_width / screen_ratio)
                        top = (img_height - new_height) // 2
                        img = img.crop((0, top, img_width, top + new_height))
                    
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.LANCZOS)
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    if image_ratio > screen_ratio:
                        new_width = SCREEN_WIDTH
                        new_height = int(SCREEN_WIDTH / image_ratio)
                    else:
                        new_height = SCREEN_HEIGHT
                        new_width = int(SCREEN_HEIGHT * image_ratio)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    background = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
                    paste_x = (SCREEN_WIDTH - new_width) // 2
                    paste_y = (SCREEN_HEIGHT - new_height) // 2
                    background.paste(img, (paste_x, paste_y))
                    img = background
                    
                else:  # "Stretch to Fit"
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.LANCZOS)
                
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                img.save(temp_img.name, "PNG", quality=95)
                temp_img_path = temp_img.name
                
                overlay = ImageClip(temp_img_path, duration=audio_duration)
                
            else:
                # VIDEO PROCESSING
                overlay = st.session_state.overlay_clip
                overlay = overlay.subclip(overlay_start, overlay_end)
                overlay_duration = overlay.duration
                st.info(f"Overlay trimmed to: {overlay_duration:.1f} seconds")
                
                orig_width, orig_height = overlay.size
                st.info(f"Original video: {orig_width} × {orig_height}, {overlay.duration:.1f}s")
                
                if overlay_duration < audio_duration:
                    loops = int(np.ceil(audio_duration / overlay_duration))
                    overlay_loops = []
                    for _ in range(loops):
                        overlay_loops.append(overlay.copy())
                    overlay = concatenate_videoclips(overlay_loops)
                    overlay = overlay.subclip(0, audio_duration)
                elif overlay_duration > audio_duration:
                    overlay = overlay.subclip(0, audio_duration)
                
                overlay_duration = overlay.duration
                
                # FIXED: Use new width/height calculation for Fit Entire option
                if fit_option == "Fill Screen (Crop if needed)":
                    # Crop to fill
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    video_ratio = orig_width / orig_height
                    
                    if video_ratio > screen_ratio:
                        crop_width = int(orig_height * screen_ratio)
                        x_center = orig_width // 2
                        overlay = overlay.crop(x1=x_center - crop_width//2, x2=x_center + crop_width//2)
                    else:
                        crop_height = int(orig_width / screen_ratio)
                        y_center = orig_height // 2
                        overlay = overlay.crop(y1=y_center - crop_height//2, y2=y_center + crop_height//2)
                    
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    # Fit with black bars - FIXED APPROACH
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    video_ratio = orig_width / orig_height
                    
                    if video_ratio > screen_ratio:
                        # Video is wider - fit to width
                        new_width = SCREEN_WIDTH
                        new_height = int(SCREEN_WIDTH / video_ratio)
                        # Resize using tuple instead of width parameter
                        overlay = overlay.resize((new_width, new_height))
                    else:
                        # Video is taller - fit to height
                        new_height = SCREEN_HEIGHT
                        new_width = int(SCREEN_HEIGHT * video_ratio)
                        # Resize using tuple instead of height parameter
                        overlay = overlay.resize((new_width, new_height))
                    
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
            
            if isinstance(overlay, CompositeVideoClip):
                overlay_with_audio = overlay.set_audio(audio_clip)
                final_video = overlay_with_audio
            else:
                overlay = overlay.set_audio(audio_clip)
                final_video = overlay
            
            final_video = final_video.set_duration(audio_duration)
            final_video = final_video.set_fps(30)
            
            # ----- STEP 4: SAVE VIDEO -----
            st.info("💾 Saving video...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            final_video.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                bitrate="10M",
                verbose=False,
                logger=None,
                threads=2,
                preset='medium',
                ffmpeg_params=['-movflags', '+faststart']
            )
            
            # Cleanup
            audio_clip.close()
            if isinstance(overlay, CompositeVideoClip):
                for clip in overlay.clips:
                    try:
                        clip.close()
                    except:
                        pass
            else:
                try:
                    overlay.close()
                except:
                    pass
            final_video.close()
            
            if 'temp_img_path' in locals():
                try:
                    os.unlink(temp_img_path)
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
    
    try:
        st.video(output_path)
    except:
        st.info("💡 Preview below - download for full quality")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Duration", f"{audio_duration:.1f}s")
        st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
    with col_info2:
        st.metric("Audio Range", f"{audio_start:.1f}s - {audio_end:.1f}s")
        st.metric("Fit Mode", fit_option)
    with col_info3:
        if not st.session_state.overlay_is_image:
            st.metric("Overlay Range", f"{overlay_start:.1f}s - {overlay_end:.1f}s")
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        st.metric("File Size", f"{file_size:.1f} MB")
    
    with open(output_path, "rb") as f:
        st.download_button(
            f"⬇ Download Fullscreen Video ({file_size:.1f} MB)",
            f,
            file_name=f"fullscreen_{SCREEN_WIDTH}x{SCREEN_HEIGHT}.mp4",
            mime="video/mp4",
            type="primary"
        )

else:
    st.markdown("""
    ## 📱 Create Fullscreen Mobile Videos
    
    ### How it works:
    1. **Upload Background** - Any audio/video file (only audio used)
    2. **Upload Overlay** - Image or video (will fill entire screen)
    3. **Adjust Durations** - Use sliders to select exact segments
    4. **Choose Fit Option** - How overlay fits on screen
    5. **Click Create** - Get fullscreen mobile video
    
    ### 🎨 Fit Options Explained:
    - **Fill Screen** - Crops edges to fill screen completely
    - **Fit Entire** - Shows entire content (black bars if needed)
    - **Stretch to Fit** - Stretches to fill (may distort)
    
    ### 📱 Perfect for:
    - Instagram Reels/TikTok with specific music cues
    - YouTube Shorts with timed overlays
    - Instagram Stories with trimmed videos
    - Mobile wallpaper videos
    """)

# ---------- CLEANUP FUNCTION ----------
def cleanup_resources():
    """Cleanup all temporary files"""
    files_to_cleanup = []
    
    if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
        files_to_cleanup.append(st.session_state.bg_path)
    if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
        files_to_cleanup.append(st.session_state.overlay_path)
    if st.session_state.bg_preview_path and os.path.exists(st.session_state.bg_preview_path):
        files_to_cleanup.append(st.session_state.bg_preview_path)
    if st.session_state.overlay_preview_path and os.path.exists(st.session_state.overlay_preview_path):
        files_to_cleanup.append(st.session_state.overlay_preview_path)
    
    if st.session_state.bg_clip:
        try:
            st.session_state.bg_clip.close()
        except:
            pass
    if st.session_state.overlay_clip:
        try:
            st.session_state.overlay_clip.close()
        except:
            pass
    if st.session_state.bg_audio_clip:
        try:
            st.session_state.bg_audio_clip.close()
        except:
            pass
    
    for file in files_to_cleanup:
        try:
            os.unlink(file)
        except:
            pass

import atexit
atexit.register(cleanup_resources)