import streamlit as st
import tempfile
import os
import sys
import gc
from PIL import Image
from io import BytesIO
import base64
import time
import mimetypes
import subprocess

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)

# ---------- MOBILE-SPECIFIC CONFIGURATION ----------
MOBILE_MAX_SIZE_MB = 50  # Reduced for mobile uploads
MOBILE_SUPPORTED_FORMATS = {
    'video': ['mp4', 'mov', 'm4v'],
    'audio': ['mp3', 'm4a', 'aac'],
    'image': ['jpg', 'jpeg', 'png', 'webp']
}

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fullscreen Video Maker (Mobile Optimized)",
    layout="centered",
    initial_sidebar_state="collapsed"  # Better for mobile
)

# Add CSS for mobile optimization
st.markdown("""
<style>
    /* Mobile-friendly adjustments */
    @media only screen and (max-width: 768px) {
        .stButton > button {
            width: 100%;
            padding: 12px;
            font-size: 16px;
        }
        .stFileUploader {
            font-size: 14px;
        }
        .element-container {
            margin-bottom: 10px;
        }
    }
    
    /* Prevent horizontal scrolling on mobile */
    .reportview-container .main .block-container {
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Progress bar styling */
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# ---------- VERSION ----------
VERSION = "2.4.0"  # Mobile optimized version
st.title(f"📱 Fullscreen Video Maker v{VERSION}")
st.caption("Mobile-optimized version")

# ---------- SESSION STATE INITIALIZATION ----------
session_defaults = {
    'bg_clip': None,
    'overlay_clip': None,
    'bg_duration': 0,
    'overlay_duration': 0,
    'bg_preview_path': None,
    'overlay_preview_path': None,
    'bg_audio_clip': None,
    'bg_path': None,
    'overlay_path': None,
    'bg_is_video': False,
    'overlay_is_image': False,
    'upload_error': None,
    'processing_status': None,
    'mobile_upload': False
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- MOBILE-DETECTION HELPER ----------
def is_mobile_user_agent():
    """Check if user is on mobile device"""
    user_agent = st.query_params.get('user_agent', '')
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    return any(keyword in user_agent.lower() for keyword in mobile_keywords)

# ---------- ENHANCED HELPER FUNCTIONS ----------
def validate_file_size(file, max_size_mb):
    """Check if file size is within mobile limits"""
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    
    size_mb = size / (1024 * 1024)
    if size_mb > max_size_mb:
        return False, size_mb
    return True, size_mb

def compress_video_for_mobile(input_path, output_path=None):
    """Compress video for mobile upload"""
    try:
        if output_path is None:
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
        
        # FFmpeg command for mobile optimization
        cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=720:-2',  # Scale to 720p for mobile
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '28',  # Higher compression
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',  # Overwrite output
            output_path
        ]
        
        # Run compression
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return output_path
        else:
            st.error(f"FFmpeg error: {result.stderr}")
            return input_path  # Return original if compression fails
    except Exception as e:
        st.warning(f"Compression skipped: {str(e)}")
        return input_path

def save_uploaded_file(uploaded_file, compress_for_mobile=False):
    """Save uploaded file with mobile optimizations"""
    try:
        # Create temp file with proper extension
        file_ext = os.path.splitext(uploaded_file.name)[1]
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=file_ext.lower()
        )
        
        # Write file in chunks for large files
        chunk_size = 1024 * 1024  # 1MB chunks
        uploaded_file.seek(0)
        
        with st.spinner(f"Saving {uploaded_file.name}..."):
            progress_bar = st.progress(0)
            data = uploaded_file.read(chunk_size)
            total_written = 0
            file_size = uploaded_file.size
            
            while data:
                temp_file.write(data)
                total_written += len(data)
                progress_bar.progress(min(total_written / file_size, 1.0))
                data = uploaded_file.read(chunk_size)
        
        temp_file.close()
        
        # Compress if needed for mobile
        if compress_for_mobile and file_ext.lower() in ['.mp4', '.mov', '.avi']:
            compressed_path = compress_video_for_mobile(temp_file.name)
            os.unlink(temp_file.name)  # Remove original
            return compressed_path
        
        return temp_file.name
        
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return None

def generate_video_preview_mobile(video_path, start_time=0, end_time=None, height=200):
    """Generate mobile-optimized preview"""
    try:
        # Use faster method for mobile
        clip = VideoFileClip(video_path, audio=False)
        
        if end_time is None or end_time > clip.duration:
            end_time = min(clip.duration, start_time + 2)  # Shorter for mobile
        
        # Ensure valid time range
        start_time = max(0, min(start_time, clip.duration - 0.1))
        end_time = max(start_time + 0.1, min(end_time, clip.duration))
        
        # Extract frame instead of GIF for faster processing
        frame_time = start_time + (end_time - start_time) / 2
        frame = clip.get_frame(frame_time)
        
        # Convert to PIL Image
        img = Image.fromarray(frame)
        img.thumbnail((height * 2, height))
        
        # Save as JPEG (smaller than PNG)
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix="_preview.jpg")
        img.save(temp_img.name, "JPEG", quality=85, optimize=True)
        temp_img.close()
        
        clip.close()
        return temp_img.name
        
    except Exception as e:
        st.warning(f"Quick preview failed, using placeholder: {str(e)}")
        # Create placeholder
        img = Image.new('RGB', (height * 2, height), color='gray')
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix="_placeholder.jpg")
        img.save(temp_img.name, "JPEG")
        temp_img.close()
        return temp_img.name

def display_mobile_warning():
    """Show mobile-specific instructions"""
    with st.expander("📱 Mobile Upload Tips", expanded=True):
        st.markdown("""
        ### For best results on mobile:
        1. **Use MP4 videos** (most compatible)
        2. **Keep files under 50MB** 
        3. **Short videos process faster**
        4. **Stay on this page** during upload
        5. **Allow camera/gallery access** if prompted
        
        ### If upload fails:
        - Try a **shorter video**
        - Convert to **MP4 format**
        - Use **WiFi connection**
        - **Refresh the page** and try again
        """)

# ---------- MOBILE UPLOAD HANDLER ----------
def handle_mobile_upload(uploaded_file, file_type="background"):
    """Special handler for mobile uploads"""
    if uploaded_file is None:
        return None
    
    # Check file size
    is_valid, size_mb = validate_file_size(uploaded_file, MOBILE_MAX_SIZE_MB)
    
    if not is_valid:
        st.session_state.upload_error = f"File too large ({size_mb:.1f}MB). Max {MOBILE_MAX_SIZE_MB}MB on mobile."
        st.error(st.session_state.upload_error)
        
        # Offer compression option
        if st.button("Try to compress automatically"):
            with st.spinner("Compressing for mobile..."):
                temp_path = save_uploaded_file(uploaded_file)
                compressed_path = compress_video_for_mobile(temp_path)
                
                if compressed_path != temp_path:
                    os.unlink(temp_path)
                    st.success(f"Compressed to {os.path.getsize(compressed_path)/(1024*1024):.1f}MB")
                    
                    # Reload with compressed file
                    with open(compressed_path, 'rb') as f:
                        uploaded_file = st.runtime.uploaded_file_manager.UploadedFile(
                            file_id=uploaded_file.file_id,
                            name=uploaded_file.name,
                            type=uploaded_file.type,
                            data=f.read()
                        )
                    return uploaded_file
        return None
    
    # Show file info
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    st.info(f"📱 Mobile upload: {uploaded_file.name} ({size_mb:.1f}MB)")
    
    return uploaded_file

# ---------- UPLOAD SECTIONS WITH MOBILE SUPPORT ----------
st.subheader("📤 Upload Media")

# Detect mobile
st.session_state.mobile_upload = is_mobile_user_agent()
if st.session_state.mobile_upload:
    display_mobile_warning()

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Background Music/Video**")
    background_file = st.file_uploader(
        "Choose background file",
        type=MOBILE_SUPPORTED_FORMATS['audio'] + MOBILE_SUPPORTED_FORMATS['video'],
        help="MP3, MP4, M4A recommended for mobile",
        key="bg_uploader",
        label_visibility="collapsed"
    )
    
    if background_file:
        # Mobile-specific handling
        if st.session_state.mobile_upload:
            background_file = handle_mobile_upload(background_file, "background")
            if background_file is None:
                st.stop()
        
        # Clear previous state
        if 'prev_bg_file' not in st.session_state or st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.bg_audio_clip = None
            st.session_state.bg_preview_path = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save and process
        with st.spinner("Processing background..."):
            bg_path = save_uploaded_file(
                background_file, 
                compress_for_mobile=st.session_state.mobile_upload
            )
            
            if bg_path:
                st.session_state.bg_path = bg_path
                bg_ext = os.path.splitext(background_file.name)[1].lower()
                st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.m4v']
                
                try:
                    if st.session_state.bg_is_video:
                        # Try faster loading method for mobile
                        st.session_state.bg_clip = VideoFileClip(bg_path, audio=True)
                        st.session_state.bg_audio_clip = st.session_state.bg_clip.audio
                        if st.session_state.bg_audio_clip is None:
                            st.warning("Video has no audio track")
                    else:
                        st.session_state.bg_clip = None
                        st.session_state.bg_audio_clip = AudioFileClip(bg_path)
                    
                    st.session_state.bg_duration = st.session_state.bg_audio_clip.duration
                    
                    # Generate preview
                    if st.session_state.bg_is_video:
                        st.session_state.bg_preview_path = generate_video_preview_mobile(
                            bg_path, 
                            start_time=0, 
                            end_time=min(2, st.session_state.bg_duration)
                        )
                    
                    st.success(f"✅ Loaded: {background_file.name}")
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if st.session_state.mobile_upload:
                        st.info("💡 Try converting to MP4 format on your device")

with col2:
    st.markdown("**Overlay (Image/Video)**")
    overlay_file = st.file_uploader(
        "Choose overlay file",
        type=MOBILE_SUPPORTED_FORMATS['image'] + MOBILE_SUPPORTED_FORMATS['video'],
        help="JPEG, PNG, MP4 recommended",
        key="overlay_uploader",
        label_visibility="collapsed"
    )
    
    if overlay_file:
        # Mobile-specific handling
        if st.session_state.mobile_upload:
            overlay_file = handle_mobile_upload(overlay_file, "overlay")
            if overlay_file is None:
                st.stop()
        
        # Clear previous state
        if 'prev_overlay_file' not in st.session_state or st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.overlay_preview_path = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save and process
        with st.spinner("Processing overlay..."):
            overlay_path = save_uploaded_file(
                overlay_file,
                compress_for_mobile=st.session_state.mobile_upload and 
                os.path.splitext(overlay_file.name)[1].lower() in ['.mp4', '.mov']
            )
            
            if overlay_path:
                st.session_state.overlay_path = overlay_path
                overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
                st.session_state.overlay_is_image = overlay_ext in ['.jpg', '.jpeg', '.png', '.webp']
                
                try:
                    if st.session_state.overlay_is_image:
                        st.session_state.overlay_clip = None
                        st.session_state.overlay_duration = 0
                        
                        # Generate image preview
                        img = Image.open(overlay_path)
                        img.thumbnail((300, 300))
                        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix="_preview.jpg")
                        img.save(temp_img.name, "JPEG", quality=90, optimize=True)
                        st.session_state.overlay_preview_path = temp_img.name
                        
                    else:
                        # Try faster video loading
                        st.session_state.overlay_clip = VideoFileClip(overlay_path, audio=False)
                        st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                        
                        # Generate preview
                        st.session_state.overlay_preview_path = generate_video_preview_mobile(
                            overlay_path,
                            start_time=0,
                            end_time=min(2, st.session_state.overlay_duration)
                        )
                    
                    st.success(f"✅ Loaded: {overlay_file.name}")
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    if st.session_state.mobile_upload:
                        st.info("💡 For videos, try MP4 format with H.264 codec")

# ---------- PREVIEW DISPLAY ----------
if st.session_state.bg_preview_path or st.session_state.overlay_preview_path:
    st.subheader("👀 Preview")
    preview_cols = st.columns(2)
    
    with preview_cols[0]:
        if st.session_state.bg_preview_path:
            if st.session_state.bg_is_video:
                st.image(st.session_state.bg_preview_path, 
                        caption=f"Background Preview ({st.session_state.bg_duration:.1f}s)",
                        use_column_width=True)
            else:
                st.info(f"🎵 Audio: {st.session_state.bg_duration:.1f} seconds")
    
    with preview_cols[1]:
        if st.session_state.overlay_preview_path:
            caption = "Image Overlay" if st.session_state.overlay_is_image else f"Video Overlay ({st.session_state.overlay_duration:.1f}s)"
            st.image(st.session_state.overlay_preview_path, 
                    caption=caption,
                    use_column_width=True)

# ---------- DURATION SELECTION (MOBILE OPTIMIZED) ----------
if st.session_state.bg_duration > 0:
    st.subheader("⏱️ Duration Settings")
    
    # Mobile-friendly simplified interface
    if st.session_state.mobile_upload:
        audio_tab, overlay_tab = st.tabs(["🎵 Audio", "🎬 Overlay"])
    else:
        audio_tab, overlay_tab = st.tabs(["🎵 Audio Settings", "🎬 Overlay Settings"])
    
    with audio_tab:
        # Simpler slider for mobile
        if st.session_state.mobile_upload:
            col1, col2 = st.columns(2)
            with col1:
                audio_start = st.number_input(
                    "Start (s)",
                    min_value=0.0,
                    max_value=float(st.session_state.bg_duration),
                    value=0.0,
                    step=0.5
                )
            with col2:
                audio_end = st.number_input(
                    "End (s)",
                    min_value=0.0,
                    max_value=float(st.session_state.bg_duration),
                    value=float(min(st.session_state.bg_duration, 30.0)),  # Shorter for mobile
                    step=0.5
                )
        else:
            col1, col2 = st.columns(2)
            with col1:
                audio_start = st.slider(
                    "Start Time",
                    0.0,
                    st.session_state.bg_duration,
                    0.0,
                    0.1,
                    key="audio_start_mobile"
                )
            with col2:
                audio_end = st.slider(
                    "End Time",
                    0.0,
                    st.session_state.bg_duration,
                    min(st.session_state.bg_duration, 60.0),  # Limit for mobile
                    0.1,
                    key="audio_end_mobile"
                )
        
        # Validate
        if audio_end <= audio_start:
            audio_end = min(audio_start + 1, st.session_state.bg_duration)
            st.warning(f"Adjusted to {audio_end:.1f}s")
        
        audio_duration = audio_end - audio_start
        st.info(f"**Audio Duration:** {audio_duration:.1f}s")
    
    with overlay_tab:
        if not st.session_state.overlay_is_image and st.session_state.overlay_duration > 0:
            if st.session_state.mobile_upload:
                col1, col2 = st.columns(2)
                with col1:
                    overlay_start = st.number_input(
                        "Start (s)",
                        min_value=0.0,
                        max_value=float(st.session_state.overlay_duration),
                        value=0.0,
                        step=0.5,
                        key="overlay_start_num"
                    )
                with col2:
                    overlay_end = st.number_input(
                        "End (s)",
                        min_value=0.0,
                        max_value=float(st.session_state.overlay_duration),
                        value=float(min(st.session_state.overlay_duration, 30.0)),
                        step=0.5,
                        key="overlay_end_num"
                    )
            else:
                overlay_start = st.slider(
                    "Overlay Start",
                    0.0,
                    st.session_state.overlay_duration,
                    0.0,
                    0.1,
                    key="overlay_start_slider"
                )
                overlay_end = st.slider(
                    "Overlay End",
                    0.0,
                    st.session_state.overlay_duration,
                    st.session_state.overlay_duration,
                    0.1,
                    key="overlay_end_slider"
                )
            
            if overlay_end <= overlay_start:
                overlay_end = min(overlay_start + 1, st.session_state.overlay_duration)
            
            st.info(f"**Overlay Duration:** {overlay_end - overlay_start:.1f}s")
        elif st.session_state.overlay_is_image:
            st.info("📸 Image overlay - will match audio duration")
        else:
            st.info("Upload overlay to adjust duration")

# ---------- SCREEN SETTINGS ----------
st.sidebar.subheader("📱 Screen Settings")

# Predefined sizes optimized for mobile
screen_presets = {
    "Instagram/TikTok (9:16)": (1080, 1920),
    "YouTube Shorts (9:16)": (1080, 1920),
    "Instagram Square (1:1)": (1080, 1080),
    "Mobile Story (9:16)": (720, 1280),
    "Custom": None
}

selected_preset = st.sidebar.selectbox(
    "Preset",
    list(screen_presets.keys()),
    index=0
)

if screen_presets[selected_preset]:
    SCREEN_WIDTH, SCREEN_HEIGHT = screen_presets[selected_preset]
else:
    SCREEN_WIDTH = st.sidebar.number_input("Width", 480, 3840, 1080, 120)
    SCREEN_HEIGHT = st.sidebar.number_input("Height", 480, 3840, 1920, 120)

st.sidebar.info(f"Resolution: {SCREEN_WIDTH}×{SCREEN_HEIGHT}")

# Fit options
st.sidebar.subheader("🎨 Fit Options")
fit_option = st.sidebar.radio(
    "Overlay Fit",
    ["Fill Screen", "Fit Entire", "Stretch"],
    index=0,
    help="Fill: crops edges, Fit: shows all, Stretch: may distort"
)

# ---------- PROCESSING FUNCTION ----------
def process_video_mobile():
    """Mobile-optimized video processing"""
    try:
        # Get durations
        audio_start = st.session_state.get('audio_start_mobile', 
                                         st.session_state.get('audio_start', 0))
        audio_end = st.session_state.get('audio_end_mobile', 
                                       st.session_state.get('audio_end', st.session_state.bg_duration))
        
        # Extract audio
        with st.spinner("🎵 Processing audio..."):
            audio_clip = st.session_state.bg_audio_clip.subclip(audio_start, audio_end)
            final_duration = audio_clip.duration
        
        # Process overlay
        with st.spinner("🖼️ Processing overlay..."):
            if st.session_state.overlay_is_image:
                # Load and resize image
                img = Image.open(st.session_state.overlay_path)
                
                if fit_option == "Fill Screen":
                    # Crop to fill
                    img_ratio = img.width / img.height
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    
                    if img_ratio > screen_ratio:
                        # Crop width
                        new_width = int(img.height * screen_ratio)
                        left = (img.width - new_width) // 2
                        img = img.crop((left, 0, left + new_width, img.height))
                    else:
                        # Crop height
                        new_height = int(img.width / screen_ratio)
                        top = (img.height - new_height) // 2
                        img = img.crop((0, top, img.width, top + new_height))
                    
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.LANCZOS)
                    
                elif fit_option == "Fit Entire":
                    # Fit with black bars
                    img_ratio = img.width / img.height
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    
                    if img_ratio > screen_ratio:
                        # Fit to width
                        new_width = SCREEN_WIDTH
                        new_height = int(SCREEN_WIDTH / img_ratio)
                    else:
                        # Fit to height
                        new_height = SCREEN_HEIGHT
                        new_width = int(SCREEN_HEIGHT * img_ratio)
                    
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    background = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
                    x = (SCREEN_WIDTH - new_width) // 2
                    y = (SCREEN_HEIGHT - new_height) // 2
                    background.paste(img, (x, y))
                    img = background
                    
                else:  # Stretch
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.LANCZOS)
                
                # Save processed image
                temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
                img.save(temp_img_path, "JPEG", quality=95)
                
                # Create image clip
                overlay = ImageClip(temp_img_path, duration=final_duration)
                
            else:
                # Video overlay
                overlay_start = st.session_state.get('overlay_start_slider', 
                                                   st.session_state.get('overlay_start_num', 0))
                overlay_end = st.session_state.get('overlay_end_slider', 
                                                 st.session_state.get('overlay_end_num', st.session_state.overlay_duration))
                
                overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
                
                # Loop if shorter than audio
                if overlay.duration < final_duration:
                    loops = int(final_duration / overlay.duration) + 1
                    overlay = concatenate_videoclips([overlay] * loops).subclip(0, final_duration)
                elif overlay.duration > final_duration:
                    overlay = overlay.subclip(0, final_duration)
                
                # Resize based on fit option
                if fit_option == "Fill Screen":
                    # Crop to fill
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    video_ratio = overlay.w / overlay.h
                    
                    if video_ratio > screen_ratio:
                        # Crop width
                        crop_width = int(overlay.h * screen_ratio)
                        x_center = overlay.w // 2
                        overlay = overlay.crop(x1=x_center-crop_width//2, x2=x_center+crop_width//2)
                    else:
                        # Crop height
                        crop_height = int(overlay.w / screen_ratio)
                        y_center = overlay.h // 2
                        overlay = overlay.crop(y1=y_center-crop_height//2, y2=y_center+crop_height//2)
                    
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                elif fit_option == "Fit Entire":
                    # Fit with black bars
                    if overlay.w/overlay.h > SCREEN_WIDTH/SCREEN_HEIGHT:
                        overlay = overlay.resize(width=SCREEN_WIDTH)
                    else:
                        overlay = overlay.resize(height=SCREEN_HEIGHT)
                    
                    background = ColorClip((SCREEN_WIDTH, SCREEN_HEIGHT), col=(0,0,0), duration=overlay.duration)
                    overlay = CompositeVideoClip([background, overlay.set_position('center')])
                    
                else:  # Stretch
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Combine audio and video
        with st.spinner("🎬 Finalizing video..."):
            final_video = overlay.set_audio(audio_clip)
            final_video = final_video.set_duration(final_duration)
            
            # Save with mobile-optimized settings
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
            
            final_video.write_videofile(
                output_path,
                fps=24 if st.session_state.mobile_upload else 30,  # Lower FPS for mobile
                codec="libx264",
                audio_codec="aac",
                bitrate="5M" if st.session_state.mobile_upload else "10M",
                threads=2,
                preset='fast',  # Faster encoding
                ffmpeg_params=['-movflags', '+faststart'],
                verbose=False,
                logger=None
            )
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        final_video.close()
        
        # Clean temp files
        if 'temp_img_path' in locals():
            try:
                os.unlink(temp_img_path)
            except:
                pass
        
        return output_path, final_duration
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        import traceback
        with st.expander("Error Details"):
            st.code(traceback.format_exc())
        return None, 0

# ---------- CREATE BUTTON ----------
st.divider()

create_disabled = not (st.session_state.bg_path and st.session_state.overlay_path)

if st.button("🚀 Create Fullscreen Video", 
             type="primary", 
             disabled=create_disabled,
             use_container_width=True):
    
    if create_disabled:
        st.warning("Please upload both background and overlay files first")
        st.stop()
    
    # Process video
    with st.status("Creating your video...", expanded=True) as status:
        output_path, video_duration = process_video_mobile()
        
        if output_path and os.path.exists(output_path):
            status.update(label="Video created successfully!", state="complete")
            
            # Display result
            st.subheader("✅ Your Video is Ready!")
            
            # Show in mobile frame
            phone_html = f"""
            <div style="
                width: 300px;
                height: {300 * SCREEN_HEIGHT/SCREEN_WIDTH}px;
                margin: 20px auto;
                border: 12px solid #333;
                border-radius: 30px;
                overflow: hidden;
                background: #000;
                position: relative;
                box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            ">
            <div style="
                position: absolute;
                top: 0;
                left: 50%;
                transform: translateX(-50%);
                width: 100px;
                height: 8px;
                background: #444;
                border-radius: 0 0 10px 10px;
            "></div>
            """
            st.markdown(phone_html, unsafe_allow_html=True)
            
            # Video preview
            try:
                st.video(output_path)
            except:
                st.info("Preview may not show on all mobile browsers")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Video info
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            info_cols = st.columns(3)
            with info_cols[0]:
                st.metric("Duration", f"{video_duration:.1f}s")
            with info_cols[1]:
                st.metric("Size", f"{file_size:.1f}MB")
            with info_cols[2]:
                st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
            
            # Download button
            with open(output_path, "rb") as f:
                st.download_button(
                    "📥 Download Video",
                    f,
                    file_name=f"fullscreen_{SCREEN_WIDTH}x{SCREEN_HEIGHT}.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True
                )
            
            # Cleanup reminder
            if st.session_state.mobile_upload:
                st.info("💡 For best quality on mobile, download and save to your device")

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How to Use (Mobile Guide)", expanded=st.session_state.mobile_upload):
    st.markdown("""
    ### Mobile-Specific Instructions:
    
    1. **Upload Files**:
       - Use **MP4 videos** for best compatibility
       - Keep files **under 50MB**
       - **JPEG/PNG images** work best
    
    2. **If Upload Fails**:
       - **Refresh the page** and try again
       - **Compress videos** before uploading
       - Use **MP3 for audio**, MP4 for video
       - Ensure **stable WiFi connection**
    
    3. **Processing Tips**:
       - **Shorter videos process faster**
       - **9:16 aspect ratio** works best for mobile
       - **'Fill Screen'** is best for social media
    
    4. **Troubleshooting**:
       - Clear browser cache if issues persist
       - Try Chrome or Safari browser
       - Update your mobile browser
    """)

# ---------- CLEANUP ----------
def cleanup():
    """Cleanup temporary files"""
    files_to_remove = [
        st.session_state.bg_path,
        st.session_state.overlay_path,
        st.session_state.bg_preview_path,
        st.session_state.overlay_preview_path
    ]
    
    for file in files_to_remove:
        if file and os.path.exists(file):
            try:
                os.unlink(file)
            except:
                pass
    
    # Force garbage collection
    gc.collect()

# Register cleanup
import atexit
atexit.register(cleanup)

# Add cleanup button in sidebar
if st.sidebar.button("🧹 Clear Cache", type="secondary"):
    cleanup()
    st.session_state.clear()
    st.rerun()

# ---------- FOOTER ----------
st.divider()
st.caption(f"v{VERSION} • Mobile Optimized • Works on iOS/Android")
