import streamlit as st
import tempfile
import os
import gc
import numpy as np
from PIL import Image
import base64
import traceback
from typing import Tuple, Optional

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ColorClip
)
from moviepy.video.fx.all import resize, crop

# ---------- APP CONFIG ----------
APP_VERSION = "2.0"  # Updated for mobile-first design
APP_TITLE = f"📱 Mobile Video Generator v{APP_VERSION}"
MOBILE_RESOLUTIONS = {
    "Portrait 9:16 (Standard)": (1080, 1920),
    "Portrait 3:4 (Instagram)": (1080, 1440),
    "Portrait 10:16 (Tall)": (1080, 1728),
    "Portrait 2:3 (Story)": (1080, 1620),
    "Custom": "custom"
}

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': f"Mobile Video Generator v{APP_VERSION} - Create portrait videos optimized for mobile devices"
    }
)

# ---------- MOBILE-FRIENDLY CSS ----------
st.markdown("""
<style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Mobile-optimized buttons */
    .stButton > button {
        width: 100%;
        height: 3em;
        font-size: 16px !important;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    /* Mobile-friendly input fields */
    .stFileUploader > div > div {
        padding: 10px;
        border-radius: 10px;
    }
    
    /* Better slider for mobile */
    .stSlider {
        padding: 10px 0;
    }
    
    /* Mobile-friendly columns */
    .stColumn {
        padding: 0 5px;
    }
    
    /* Video player responsive */
    .stVideo {
        border-radius: 15px;
        overflow: hidden;
        margin: 10px 0;
    }
    
    /* Metric cards */
    .stMetric {
        background-color: rgba(240, 242, 246, 0.5);
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    /* Expandable sections */
    .streamlit-expanderHeader {
        font-size: 18px !important;
        padding: 15px !important;
    }
    
    /* Hide Streamlit branding for mobile */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Touch-friendly controls */
    .stSlider > div > div > div {
        height: 8px;
    }
    
    .stSlider > div > div > div > div {
        height: 20px;
        width: 20px;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #FF4B4B;
    }
    
    @media only screen and (max-width: 768px) {
        /* Mobile-specific adjustments */
        .stApp {
            padding: 10px;
        }
        h1 {
            font-size: 24px !important;
        }
        h2 {
            font-size: 20px !important;
        }
        h3 {
            font-size: 18px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(APP_TITLE)
st.caption("🎯 Create perfect portrait videos for mobile - All dimensions supported")

# ---------- SESSION STATE ----------
session_defaults = {
    'bg_clip': None,
    'overlay_clip': None,
    'bg_duration': 0,
    'overlay_duration': 0,
    'bg_path': None,
    'overlay_path': None,
    'bg_is_video': False,
    'overlay_is_image': False,
    'prev_bg_file': None,
    'prev_overlay_file': None,
    'selected_resolution': list(MOBILE_RESOLUTIONS.keys())[0],
    'custom_width': 1080,
    'custom_height': 1920,
    'fit_mode': 'cover',  # 'cover', 'contain', 'stretch'
    'bg_color': '#000000',
    'output_path': None
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- MOBILE-SPECIFIC FUNCTIONS ----------
def detect_mobile_browser() -> bool:
    """Detect if user is accessing from mobile browser"""
    user_agent = st.request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
    return any(keyword in user_agent for keyword in mobile_keywords)

def save_uploaded_file_mobile(uploaded_file, max_size_mb: int = 500):
    """Save uploaded file with mobile-friendly optimizations"""
    # Check file size for mobile constraints
    file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
    if file_size > max_size_mb:
        st.warning(f"⚠️ File size ({file_size:.1f}MB) exceeds recommended limit ({max_size_mb}MB) for mobile processing")
        if detect_mobile_browser():
            st.info("For better performance on mobile, please use files under 100MB")
    
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, 
        suffix=os.path.splitext(uploaded_file.name)[1]
    )
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def get_mobile_resolution() -> Tuple[int, int]:
    """Get selected mobile resolution"""
    if st.session_state.selected_resolution == "Custom":
        return (st.session_state.custom_width, st.session_state.custom_height)
    else:
        return MOBILE_RESOLUTIONS[st.session_state.selected_resolution]

def create_mobile_compatible_video(original_clip, target_width: int, target_height: int, fit_mode: str, bg_color: str) -> VideoFileClip:
    """Resize and format video for mobile portrait display"""
    
    # Get original dimensions
    orig_width, orig_height = original_clip.size
    orig_ratio = orig_width / orig_height
    target_ratio = target_width / target_height
    
    if fit_mode == 'stretch':
        # Simply stretch to target resolution
        resized_clip = resize(original_clip, (target_width, target_height))
        return resized_clip
    
    elif fit_mode == 'cover':
        # Crop to fill entire frame (no black bars)
        if orig_ratio > target_ratio:
            # Original is wider, crop height
            new_height = orig_height
            new_width = int(target_ratio * new_height)
        else:
            # Original is taller, crop width
            new_width = orig_width
            new_height = int(new_width / target_ratio)
        
        # Calculate crop position (center)
        x_center = orig_width / 2
        y_center = orig_height / 2
        
        cropped_clip = crop(
            original_clip,
            x1=int(x_center - new_width/2),
            y1=int(y_center - new_height/2),
            width=new_width,
            height=new_height
        )
        
        # Resize to target
        resized_clip = resize(cropped_clip, (target_width, target_height))
        return resized_clip
    
    else:  # 'contain' mode
        # Fit within frame with letterbox/pillarbox
        if orig_ratio > target_ratio:
            # Fit to width
            new_width = target_width
            new_height = int(new_width / orig_ratio)
        else:
            # Fit to height
            new_height = target_height
            new_width = int(new_height * orig_ratio)
        
        # Resize maintaining aspect ratio
        resized_clip = resize(original_clip, (new_width, new_height))
        
        # Create background color clip
        background = ColorClip(
            size=(target_width, target_height),
            color=[int(bg_color[i:i+2], 16) for i in (1, 3, 5)]
        ).set_duration(resized_clip.duration)
        
        # Calculate position (center)
        x_pos = (target_width - new_width) // 2
        y_pos = (target_height - new_height) // 2
        
        # Composite video on background
        final_clip = CompositeVideoClip([
            background,
            resized_clip.set_position((x_pos, y_pos))
        ])
        
        return final_clip

def optimize_for_mobile_export(clip, target_resolution: Tuple[int, int]) -> VideoFileClip:
    """Apply mobile-specific optimizations for export"""
    # Ensure portrait orientation
    width, height = clip.size
    if width > height:
        # Landscape detected - rotate if needed
        st.warning("⚠️ Landscape video detected. Auto-rotating for portrait mobile display.")
        clip = clip.rotate(90)
        width, height = clip.size
    
    # Apply mobile-friendly encoding settings
    clip = clip.set_fps(min(clip.fps, 60))  # Cap at 60fps for mobile
    return clip

def show_mobile_preview(video_path: str, resolution: Tuple[int, int]) -> Optional[Image.Image]:
    """Show preview optimized for mobile display"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        
        # Get frame at 25% duration
        preview_time = clip.duration * 0.25
        if preview_time > clip.duration:
            preview_time = clip.duration / 2
        
        frame = clip.get_frame(preview_time)
        img = Image.fromarray(frame)
        
        # Resize preview for mobile display
        preview_width, preview_height = resolution
        if preview_width > 400:  # Limit preview size for mobile
            scale = 400 / preview_width
            preview_width = int(preview_width * scale)
            preview_height = int(preview_height * scale)
        
        img.thumbnail((preview_width, preview_height))
        
        clip.close()
        return img
    except Exception as e:
        st.warning(f"Preview generation failed: {str(e)}")
        return None

# ---------- MOBILE-FRIENDLY UI LAYOUT ----------
# Detect mobile browser
is_mobile = detect_mobile_browser()
if is_mobile:
    st.info("📱 Mobile browser detected - Interface optimized for touch")

# Main layout with mobile-friendly columns
st.subheader("📁 Upload Your Media")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "**Background Audio/Video**",
        type=["mp3", "wav", "m4a", "mp4", "mov", "avi"],
        help="Audio will be extracted from this file. MP3 recommended for mobile.",
        key="bg_uploader"
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        with st.spinner("Loading background..."):
            st.session_state.bg_path = save_uploaded_file_mobile(background_file)
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi']
            
            try:
                if st.session_state.bg_is_video:
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        st.success(f"✅ Video loaded: {background_file.name[:20]}... ({st.session_state.bg_duration:.1f}s)")
                    else:
                        st.error("No audio track found in video")
                        st.stop()
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                    st.success(f"✅ Audio loaded: {background_file.name[:20]}... ({st.session_state.bg_duration:.1f}s)")
                
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
                if is_mobile:
                    st.info("💡 Tip: Try converting to MP3/MP4 format for better mobile compatibility")

with col2:
    overlay_file = st.file_uploader(
        "**Overlay Video/Image**",
        type=["mp4", "mov", "avi", "jpg", "jpeg", "png", "gif"],
        help="Video or image overlay. All formats supported.",
        key="overlay_uploader"
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        with st.spinner("Loading overlay..."):
            st.session_state.overlay_path = save_uploaded_file_mobile(overlay_file)
            overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
            st.session_state.overlay_is_image = overlay_ext in ['.jpg', '.jpeg', '.png', '.gif']
            
            try:
                if st.session_state.overlay_is_image:
                    # Handle image as video clip
                    img = Image.open(st.session_state.overlay_path)
                    img_array = np.array(img)
                    st.session_state.overlay_clip = ImageClip(img_array, duration=10)  # Default 10s for images
                    st.session_state.overlay_duration = 10
                    st.success(f"✅ Image loaded: {overlay_file.name[:20]}...")
                    
                    # Show preview
                    st.image(img, caption="Image Preview", use_column_width=True)
                else:
                    # Handle video
                    st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    st.success(f"✅ Video loaded: {overlay_file.name[:20]}... ({st.session_state.overlay_duration:.1f}s)")
                    
                    # Show mobile-optimized preview
                    target_res = get_mobile_resolution()
                    preview_img = show_mobile_preview(st.session_state.overlay_path, target_res)
                    if preview_img:
                        st.image(preview_img, caption="Mobile Preview", use_column_width=True)
                        
            except Exception as e:
                st.error(f"Error loading overlay: {str(e)}")

# ---------- MOBILE VIDEO SETTINGS ----------
st.subheader("⚙️ Mobile Video Settings")

settings_col1, settings_col2, settings_col3 = st.columns(3)

with settings_col1:
    st.session_state.selected_resolution = st.selectbox(
        "Mobile Resolution",
        options=list(MOBILE_RESOLUTIONS.keys()),
        index=0,
        help="Select standard mobile portrait resolution"
    )
    
    if st.session_state.selected_resolution == "Custom":
        col_custom1, col_custom2 = st.columns(2)
        with col_custom1:
            st.session_state.custom_width = st.number_input("Width", min_value=480, max_value=3840, value=1080, step=10)
        with col_custom2:
            st.session_state.custom_height = st.number_input("Height", min_value=480, max_value=3840, value=1920, step=10)

with settings_col2:
    st.session_state.fit_mode = st.selectbox(
        "Fit Mode",
        options=['cover', 'contain', 'stretch'],
        format_func=lambda x: {
            'cover': 'Fill Screen (Crop)',
            'contain': 'Fit to Screen (Letterbox)',
            'stretch': 'Stretch to Fit'
        }[x],
        help="How to handle different aspect ratios"
    )
    
    if st.session_state.fit_mode == 'contain':
        st.session_state.bg_color = st.color_picker(
            "Background Color",
            value="#000000",
            help="Color for letterbox/pillarbox areas"
        )

with settings_col3:
    # Show selected resolution preview
    target_width, target_height = get_mobile_resolution()
    st.metric("Target Resolution", f"{target_width} × {target_height}")
    st.caption(f"Aspect ratio: {target_width/target_height:.2f}:1")

# ---------- TRIM SETTINGS (MOBILE-OPTIMIZED) ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    # Mobile-friendly trim interface
    if is_mobile:
        # Simplified interface for mobile
        audio_start = st.slider(
            "Audio Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            0.0,
            0.5,
            key="audio_start_mobile"
        )
        
        audio_end = st.slider(
            "Audio End (seconds)",
            float(audio_start),
            float(st.session_state.bg_duration),
            min(float(st.session_state.bg_duration), float(audio_start) + 30.0),
            0.5,
            key="audio_end_mobile"
        )
        
        audio_duration = audio_end - audio_start
        st.info(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)")
    else:
        # Advanced interface for desktop
        col_trim1, col_trim2 = st.columns(2)
        
        with col_trim1:
            audio_start = st.slider(
                "Audio Start",
                0.0,
                float(st.session_state.bg_duration),
                0.0,
                0.1,
                key="audio_start_desktop"
            )
        
        with col_trim2:
            max_audio_end = st.session_state.bg_duration
            audio_duration_val = st.slider(
                "Audio Duration",
                1.0,
                float(max_audio_end - audio_start),
                min(30.0, float(max_audio_end - audio_start)),
                0.1,
                key="audio_duration_desktop"
            )
            
            audio_end = audio_start + audio_duration_val
            st.info(f"Duration: {audio_duration_val:.1f}s")

if st.session_state.overlay_duration > 0:
    # Overlay trim settings
    overlay_start = st.slider(
        "Overlay Start (seconds)",
        0.0,
        float(st.session_state.overlay_duration),
        0.0,
        0.5,
        key="overlay_start"
    )
    
    max_overlay_duration = st.session_state.overlay_duration - overlay_start
    overlay_duration_val = st.slider(
        "Overlay Duration",
        1.0,
        float(max_overlay_duration),
        min(float(st.session_state.bg_duration) if st.session_state.bg_duration > 0 else 30.0, 
            float(max_overlay_duration)),
        0.5,
        key="overlay_duration"
    )
    
    overlay_end = overlay_start + overlay_duration_val
    st.info(f"🎬 Overlay: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration_val:.1f}s)")

# ---------- PROCESS FUNCTION FOR MOBILE ----------
def process_mobile_video():
    """Create mobile-optimized portrait video"""
    try:
        # Get trim values
        audio_start = st.session_state.get('audio_start_mobile', 
                                         st.session_state.get('audio_start_desktop', 0))
        audio_end = st.session_state.get('audio_end_mobile', 
                                       st.session_state.get('audio_start_desktop', 0) + 
                                       st.session_state.get('audio_duration_desktop', 30))
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_end = st.session_state.get('overlay_start', 0) + \
                     st.session_state.get('overlay_duration', 30)
        
        # Get mobile settings
        target_width, target_height = get_mobile_resolution()
        fit_mode = st.session_state.fit_mode
        bg_color = st.session_state.bg_color
        
        with st.spinner("🎵 Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Progress indicator
        progress_bar = st.progress(0)
        
        with st.spinner("📱 Processing video for mobile..."):
            # Trim overlay
            overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
            progress_bar.progress(25)
            
            # Loop overlay if shorter than audio
            if overlay.duration < final_audio_duration:
                loops_needed = int(final_audio_duration / overlay.duration) + 1
                overlay_loops = [overlay] * loops_needed
                overlay = concatenate_videoclips(overlay_loops)
                overlay = overlay.subclip(0, final_audio_duration)
            elif overlay.duration > final_audio_duration:
                overlay = overlay.subclip(0, final_audio_duration)
            
            progress_bar.progress(50)
            
            # Resize for mobile
            mobile_clip = create_mobile_compatible_video(
                overlay, 
                target_width, 
                target_height, 
                fit_mode, 
                bg_color
            )
            progress_bar.progress(75)
            
            # Optimize for mobile
            mobile_clip = optimize_for_mobile_export(mobile_clip, (target_width, target_height))
            
            # Add audio
            final_video = mobile_clip.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
            
            progress_bar.progress(90)
            
        with st.spinner("💾 Saving mobile video..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
            
            # Mobile-optimized encoding settings
            bitrate = "5M" if target_height <= 1080 else "8M"
            
            final_video.write_videofile(
                output_path,
                fps=min(final_video.fps, 30),  # Lower fps for mobile
                codec="libx264",
                audio_codec="aac",
                bitrate=bitrate,
                audio_bitrate="192k",
                threads=2,  # Reduce threads for mobile compatibility
                preset='fast',  # Faster encoding
                ffmpeg_params=[
                    '-movflags', '+faststart',
                    '-profile:v', 'baseline',  # Better mobile compatibility
                    '-level', '3.0',
                    '-pix_fmt', 'yuv420p'  # Ensure compatibility
                ],
                verbose=False,
                logger=None
            )
            
            progress_bar.progress(100)
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        mobile_clip.close()
        final_video.close()
        
        return output_path, final_audio_duration, target_width, target_height
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
        with st.expander("Error details for debugging"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0

# ---------- CREATE BUTTON (MOBILE OPTIMIZED) ----------
st.divider()

files_ready = st.session_state.bg_path and st.session_state.overlay_path

# Create two columns for buttons
if is_mobile:
    create_col, _ = st.columns([3, 1])
else:
    create_col = st

with create_col:
    if st.button("🚀 CREATE MOBILE VIDEO", 
                 type="primary", 
                 disabled=not files_ready,
                 use_container_width=True,
                 help="Generate portrait video optimized for mobile devices"):
        
        if not files_ready:
            st.warning("Please upload both background and overlay files first")
            st.stop()
        
        # Check if we're on mobile browser with large files
        if is_mobile:
            bg_size = os.path.getsize(st.session_state.bg_path) / (1024 * 1024)
            overlay_size = os.path.getsize(st.session_state.overlay_path) / (1024 * 1024)
            
            if bg_size > 100 or overlay_size > 100:
                st.warning("⚠️ Large files detected on mobile. Processing may take longer.")
        
        # Process video
        with st.spinner("Creating your mobile video..."):
            output_path, duration, width, height = process_mobile_video()
        
        if output_path and os.path.exists(output_path):
            st.session_state.output_path = output_path
            
            st.success("✅ Mobile video created successfully!")
            st.balloons()
            
            # Show video preview
            st.subheader("📱 Your Mobile Video")
            
            try:
                # Encode video for display
                with open(output_path, "rb") as f:
                    video_bytes = f.read()
                
                # Display video with mobile aspect ratio
                st.video(video_bytes)
                
            except Exception as e:
                st.info("Video preview loaded. Download to view on your device.")
            
            # Video info
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                st.metric("Duration", f"{duration:.1f}s")
            with col_info2:
                st.metric("Resolution", f"{width}×{height}")
            with col_info3:
                st.metric("File Size", f"{file_size:.1f}MB")
            
            # Download button
            st.subheader("📥 Download")
            
            with open(output_path, "rb") as f:
                video_data = f.read()
            
            # Generate descriptive filename
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"mobile_video_{width}x{height}_{timestamp}.mp4"
            
            st.download_button(
                label="DOWNLOAD MOBILE VIDEO",
                data=video_data,
                file_name=filename,
                mime="video/mp4",
                type="secondary",
                use_container_width=True,
                help="Download portrait video optimized for mobile devices"
            )
            
            # Cleanup instructions
            with st.expander("🗑️ Cleanup Options"):
                st.info("Temporary files will be automatically cleaned up. For large files, consider:")
                st.markdown("""
                1. **Close the browser tab** when done
                2. **Clear browser cache** if storage is full
                3. **Download promptly** - files are temporary
                """)
            
            # Force cleanup
            gc.collect()

# ---------- MOBILE TROUBLESHOOTING GUIDE ----------
with st.expander("🔧 Mobile Troubleshooting Guide", expanded=is_mobile):
    st.markdown("""
    ### Common Mobile Issues & Solutions:
    
    **📱 Browser Issues:**
    - **Chrome Mobile**: Works best - enable desktop site for larger files
    - **Safari iOS**: May have 50MB limit - use smaller files
    - **Firefox Mobile**: Good for large files
    
    **⚠️ Processing Failures:**
    - **Large Files**: Compress videos to <100MB before uploading
    - **Unsupported Codecs**: Convert to MP4 (H.264/AAC) first
    - **Slow Processing**: Use lower resolutions (720p instead of 1080p)
    
    **🎯 Mobile-Specific Tips:**
    1. **Portrait First**: Upload portrait videos for best results
    2. **Wi-Fi Recommended**: Use Wi-Fi for files >20MB
    3. **Close Apps**: Close other apps for better performance
    4. **Update Browser**: Use latest browser version
    
    **💡 Recommended Settings for Mobile:**
    - Resolution: 1080x1920 (Standard Portrait)
    - Fit Mode: "Fill Screen" for social media
    - File Format: MP4 with H.264 codec
    - Max File Size: 50MB for best performance
    """)
    
    if is_mobile:
        st.warning("**You're on mobile!** For best results, use Wi-Fi and keep the screen active during processing.")

# ---------- INSTRUCTIONS FOR MOBILE ----------
with st.expander("📖 How to Create Perfect Mobile Videos", expanded=not is_mobile):
    st.markdown("""
    ## 📱 Mobile Video Creation Guide
    
    ### **Step-by-Step Process:**
    
    1. **Upload Media**
       - **Background**: Audio file (MP3) or Video with audio
       - **Overlay**: Video or Image to display
    
    2. **Select Mobile Settings**
       - Choose **portrait resolution** (9:16 recommended)
       - Select **fit mode**:
         - *Fill Screen*: Crops to fill (best for Stories/Reels)
         - *Fit to Screen*: Shows entire video with borders
         - *Stretch*: Distorts to fit (use cautiously)
    
    3. **Trim Content**
       - Set exact start/end points for both audio and video
       - Match durations for perfect sync
    
    4. **Generate & Download**
       - Creates portrait video optimized for mobile
       - Automatic format conversion for compatibility
       - One-click download to your device
    
    ### **Best Practices:**
    - **For Instagram/Stories**: Use 1080x1920 with "Fill Screen"
    - **For TikTok/Reels**: Use 1080x1920, keep under 60 seconds
    - **For WhatsApp/Status**: Use 720x1280 for faster sharing
    - **For YouTube Shorts**: Use 1080x1920, vertical video
    
    ### **Mobile-Optimized Features:**
    ✅ **Portrait-first design**  
    ✅ **Touch-friendly controls**  
    ✅ **Mobile browser support**  
    ✅ **Automatic rotation handling**  
    ✅ **Efficient encoding for mobile**  
    ✅ **Small file sizes for sharing**  
    """)

# ---------- FOOTER WITH MOBILE INFO ----------
st.divider()
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption(f"Version {APP_VERSION}")

with footer_col2:
    if is_mobile:
        st.caption("📱 Mobile Mode Active")
    else:
        st.caption("💻 Desktop Mode")

with footer_col3:
    st.caption("Optimized for portrait mobile video")

# ---------- AUTO-CLEANUP ON EXIT ----------
def cleanup_temp_files():
    """Clean up temporary files"""
    temp_files = [
        st.session_state.get('bg_path'),
        st.session_state.get('overlay_path'),
        st.session_state.get('output_path')
    ]
    
    for file_path in temp_files:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass

# Register cleanup
import atexit
atexit.register(cleanup_temp_files)
