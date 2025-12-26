import streamlit as st
import tempfile
import os
import gc
from PIL import Image, ImageFilter
import base64
import time
import numpy as np

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ColorClip
)

# Update version
my_title = "🎬 Smart Mobile Video Maker V 25"

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title=my_title,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# ---------- CSS ----------
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    .stButton > button { width: 100%; min-height: 44px; }
    @media (max-width: 768px) {
        .main .block-container { padding: 1rem; }
        h1 { font-size: 1.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("📱 Smart detection - Keeps mobile videos as-is, converts only landscape videos")

# ---------- SESSION STATE ----------
session_defaults = {
    'bg_clip': None, 'overlay_clip': None, 'bg_duration': 0, 'overlay_duration': 0,
    'bg_path': None, 'overlay_path': None, 'bg_is_video': False, 'processing': False,
    'prev_bg_file': None, 'prev_overlay_file': None, 'video_info': None
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- TARGET RESOLUTIONS ----------
PORTRAIT_HD = (1080, 1920)      # 9:16 Full HD Portrait
PORTRAIT_SD = (720, 1280)       # 9:16 HD Portrait
LANDSCAPE_HD = (1920, 1080)     # 16:9 Full HD

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    try:
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(uploaded_file.name)[1]
        )
        temp_file.write(uploaded_file.getvalue())
        temp_file.close()
        return temp_file.name
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return None

def analyze_video(video_path):
    """Analyze video properties and determine best output format"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        width, height = clip.size
        aspect_ratio = width / height
        
        # Determine video type
        if height > width:  # Portrait
            video_type = "portrait"
            target_resolution = (min(1080, width), min(1920, height))  # Keep original or max 1080x1920
        elif width > height:  # Landscape
            video_type = "landscape"
            # For landscape, convert to portrait with smart cropping
            target_resolution = PORTRAIT_HD
        else:  # Square
            video_type = "square"
            target_resolution = PORTRAIT_SD
        
        info = {
            'width': width,
            'height': height,
            'aspect_ratio': round(aspect_ratio, 2),
            'video_type': video_type,
            'target_resolution': target_resolution,
            'fps': clip.fps if hasattr(clip, 'fps') else 30,
            'duration': clip.duration
        }
        
        clip.close()
        return info
        
    except Exception as e:
        st.error(f"Error analyzing video: {str(e)}")
        return None

def show_preview(video_path):
    """Show preview of video"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if clip.duration == 0:
            clip.close()
            return None
        
        # Get frame at 1 second or middle
        time_point = min(1, clip.duration / 2)
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Create thumbnail
        img.thumbnail((300, 300))
        
        # Add aspect ratio info
        width, height = clip.size
        clip.close()
        
        return img, width, height
    except:
        return None, 0, 0

def resize_for_mobile(clip, video_info):
    """Smart resize for mobile - only convert if needed"""
    try:
        width, height = clip.size
        target_width, target_height = video_info['target_resolution']
        
        # If already mobile portrait and similar size, keep as-is
        if video_info['video_type'] == 'portrait':
            # Check if close enough to target (within 10%)
            width_diff = abs(width - target_width) / target_width
            height_diff = abs(height - target_height) / target_height
            
            if width_diff < 0.1 and height_diff < 0.1:
                # Already mobile portrait, no resize needed
                return clip
            else:
                # Resize to target maintaining aspect ratio
                return clip.resize((target_width, target_height))
        
        elif video_info['video_type'] == 'landscape':
            # Convert landscape to portrait with smart crop
            return convert_landscape_to_portrait(clip, target_width, target_height)
        
        else:  # Square
            # Convert square to portrait with padding
            return convert_square_to_portrait(clip, target_width, target_height)
            
    except Exception as e:
        st.error(f"Error resizing: {str(e)}")
        return clip

def convert_landscape_to_portrait(clip, target_width, target_height):
    """Convert landscape video to portrait with smart cropping"""
    try:
        width, height = clip.size
        
        # Method 1: Crop center (good for talking heads in center)
        crop_width = width
        crop_height = int(width * (target_height / target_width))  # Maintain 9:16
        
        if crop_height <= height:
            # Can crop from center
            y1 = (height - crop_height) // 2
            y2 = y1 + crop_height
            return clip.crop(y1=y1, y2=y2).resize((target_width, target_height))
        else:
            # Need to scale first
            scale = target_width / width
            new_height = int(height * scale)
            resized = clip.resize((target_width, new_height))
            
            # Then crop or pad
            if new_height >= target_height:
                # Crop from center
                y1 = (new_height - target_height) // 2
                return resized.crop(y1=y1, y2=y1 + target_height)
            else:
                # Add black bars
                x_pos = 0
                y_pos = (target_height - new_height) // 2
                
                background = ColorClip(
                    size=(target_width, target_height),
                    color=(0, 0, 0),
                    duration=clip.duration
                )
                
                return CompositeVideoClip([
                    background,
                    resized.set_position((x_pos, y_pos))
                ])
                
    except Exception as e:
        st.error(f"Error converting landscape: {str(e)}")
        return clip.resize((target_width, target_height))

def convert_square_to_portrait(clip, target_width, target_height):
    """Convert square video to portrait"""
    try:
        width, height = clip.size
        
        # Scale to target width
        scale = target_width / width
        new_height = int(height * scale)
        resized = clip.resize((target_width, new_height))
        
        # Add black bars top and bottom
        x_pos = 0
        y_pos = (target_height - new_height) // 2
        
        background = ColorClip(
            size=(target_width, target_height),
            color=(0, 0, 0),
            duration=clip.duration
        )
        
        return CompositeVideoClip([
            background,
            resized.set_position((x_pos, y_pos))
        ])
        
    except Exception as e:
        st.error(f"Error converting square: {str(e)}")
        return clip.resize((target_width, target_height))

# ---------- UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a"],
        help="Audio will be extracted from this file"
    )

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov"],
        help="Video will be smart-converted for mobile"
    )

# ---------- BACKGROUND FILE HANDLING ----------
if background_file and st.session_state.prev_bg_file != background_file.name:
    st.session_state.prev_bg_file = background_file.name
    
    with st.spinner("Loading background..."):
        bg_path = save_uploaded_file(background_file)
        if bg_path:
            st.session_state.bg_path = bg_path
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
            
            try:
                if st.session_state.bg_is_video:
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        st.success(f"✅ Video loaded: {st.session_state.bg_duration:.1f}s")
                    else:
                        st.error("⚠️ No audio in video")
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                    st.success(f"✅ Audio loaded: {st.session_state.bg_duration:.1f}s")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ---------- OVERLAY FILE HANDLING ----------
if overlay_file and st.session_state.prev_overlay_file != overlay_file.name:
    st.session_state.prev_overlay_file = overlay_file.name
    
    with st.spinner("Analyzing video..."):
        overlay_path = save_uploaded_file(overlay_file)
        if overlay_path:
            st.session_state.overlay_path = overlay_path
            
            try:
                # Load and analyze video
                st.session_state.overlay_clip = VideoFileClip(overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                # Analyze video properties
                st.session_state.video_info = analyze_video(overlay_path)
                
                if st.session_state.video_info:
                    info = st.session_state.video_info
                    width, height = info['width'], info['height']
                    target_w, target_h = info['target_resolution']
                    
                    st.success(f"✅ {overlay_file.name} loaded: {st.session_state.overlay_duration:.1f}s")
                    
                    # Show video info
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Original", f"{width}×{height}")
                    with col2:
                        st.metric("Type", info['video_type'].title())
                    with col3:
                        st.metric("Target", f"{target_w}×{target_h}")
                    
                    # Show preview
                    preview_img, preview_w, preview_h = show_preview(overlay_path)
                    if preview_img:
                        st.image(preview_img, caption=f"Preview ({preview_w}×{preview_h})", use_container_width=True)
                    
                    # Show conversion note
                    if info['video_type'] == 'portrait':
                        st.info(f"📱 This is already a mobile portrait video. Will be kept at {target_w}×{target_h}")
                    elif info['video_type'] == 'landscape':
                        st.warning(f"🔄 Landscape video will be converted to portrait {target_w}×{target_h}")
                    else:
                        st.info(f"⬛ Square video will be converted to portrait {target_w}×{target_h}")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        audio_start = st.slider(
            "Audio Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            0.0,
            0.5,
            key="audio_start"
        )
    
    with col2:
        max_audio_duration = st.session_state.bg_duration - audio_start
        default_duration = min(30.0, float(max_audio_duration))
        
        audio_duration = st.slider(
            "Audio Duration (seconds)",
            1.0,
            float(max_audio_duration),
            default_duration,
            0.5,
            key="audio_duration"
        )
    
    audio_end = audio_start + audio_duration
    st.success(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s total)")

if st.session_state.overlay_duration > 0:
    col1, col2 = st.columns(2)
    
    with col1:
        overlay_start = st.slider(
            "Overlay Start (seconds)",
            0.0,
            float(st.session_state.overlay_duration),
            0.0,
            0.5,
            key="overlay_start"
        )
    
    with col2:
        max_overlay_duration = st.session_state.overlay_duration - overlay_start
        default_duration = min(30.0, float(max_overlay_duration))
        
        overlay_duration = st.slider(
            "Overlay Duration (seconds)",
            1.0,
            float(max_overlay_duration),
            default_duration,
            0.5,
            key="overlay_duration"
        )
    
    overlay_end = overlay_start + overlay_duration
    st.success(f"📹 Overlay: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")

# ---------- PROCESS FUNCTION ----------
def process_smart_video():
    """Smart processing - keeps mobile videos as-is, converts others"""
    try:
        st.session_state.processing = True
        
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 
                                                 min(30, st.session_state.bg_duration))
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration',
                                                   min(30, st.session_state.overlay_duration))
        overlay_end = overlay_start + overlay_duration_val
        
        # Progress bar
        progress_bar = st.progress(0, text="Starting...")
        
        # Extract audio
        progress_bar.progress(20, text="Extracting audio...")
        if st.session_state.bg_is_video and st.session_state.bg_clip:
            audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Trim overlay
        progress_bar.progress(40, text="Trimming overlay...")
        overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
        
        # Match durations
        progress_bar.progress(60, text="Matching durations...")
        if overlay.duration < final_audio_duration:
            loops_needed = int(final_audio_duration / overlay.duration) + 1
            overlay_loops = [overlay] * loops_needed
            overlay = concatenate_videoclips(overlay_loops)
            overlay = overlay.subclip(0, final_audio_duration)
        elif overlay.duration > final_audio_duration:
            overlay = overlay.subclip(0, final_audio_duration)
        
        # Smart resize for mobile
        progress_bar.progress(80, text="Optimizing for mobile...")
        
        if st.session_state.video_info:
            # Use smart resize based on video type
            mobile_video = resize_for_mobile(overlay, st.session_state.video_info)
        else:
            # Fallback to portrait
            mobile_video = overlay.resize(PORTRAIT_HD)
        
        # Add audio
        progress_bar.progress(90, text="Adding audio...")
        final_video = mobile_video.set_audio(audio_clip)
        final_video = final_video.set_duration(final_audio_duration)
        
        # Save video
        progress_bar.progress(95, text="Saving video...")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
        
        # Get final dimensions
        final_width, final_height = mobile_video.size
        
        # Write video
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8M",
            verbose=False,
            logger=None,
            preset='medium',
            ffmpeg_params=['-movflags', '+faststart']
        )
        
        progress_bar.progress(100, text="Complete!")
        time.sleep(0.5)
        progress_bar.empty()
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        mobile_video.close()
        final_video.close()
        
        return output_path, final_audio_duration, final_width, final_height
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None, 0, 0, 0
    finally:
        st.session_state.processing = False

# ---------- CREATE BUTTON ----------
st.divider()

files_ready = st.session_state.bg_path and st.session_state.overlay_path
button_text = "⏳ Processing..." if st.session_state.processing else "🎬 Create Smart Mobile Video"

if st.button(
    button_text,
    type="primary",
    disabled=not files_ready or st.session_state.processing,
    use_container_width=True
):
    if not files_ready:
        st.warning("Please upload both files first")
        st.stop()
    
    # Show processing info
    if st.session_state.video_info:
        info = st.session_state.video_info
        st.info(f"🔄 Processing: {info['width']}×{info['height']} {info['video_type']} → {info['target_resolution'][0]}×{info['target_resolution'][1]}")
    
    # Process video
    output_path, duration, width, height = process_smart_video()
    
    if output_path and os.path.exists(output_path):
        st.balloons()
        st.success(f"✅ Mobile video created: {width}×{height}")
        
        # Show video
        st.subheader("🎥 Your Mobile Video")
        
        try:
            video_bytes = open(output_path, "rb").read()
            st.video(video_bytes)
        except:
            st.info("Video ready for download")
        
        # Show info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Size", f"{file_size:.1f}MB")
        
        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "📥 Download Video",
                f.read(),
                file_name=f"mobile_video_{width}x{height}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Cleanup
        try:
            if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
                os.unlink(st.session_state.bg_path)
            if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
                os.unlink(st.session_state.overlay_path)
        except:
            pass
        
        # Clear session
        if st.session_state.bg_clip:
            try:
                st.session_state.bg_clip.close()
            except:
                pass
            st.session_state.bg_clip = None
            
        if st.session_state.overlay_clip:
            try:
                st.session_state.overlay_clip.close()
            except:
                pass
            st.session_state.overlay_clip = None
        
        gc.collect()

# ---------- HOW IT WORKS ----------
with st.expander("📖 How It Works", expanded=True):
    st.markdown("""
    ### Smart Mobile Video Maker
    
    **Key Features:**
    
    1. **Smart Detection**
       - Detects if video is already mobile/portrait
       - Keeps mobile videos as-is (no unnecessary resizing)
       - Only converts landscape videos to portrait
    
    2. **Intelligent Conversion**
       - **Portrait videos:** Keeps original size (up to 1080×1920)
       - **Landscape videos:** Smart crop to 9:16 portrait
       - **Square videos:** Adds black bars for portrait
    
    3. **Preserves Quality**
       - No stretching or unnatural resizing
       - Maintains aspect ratio
       - Keeps important content centered
    
    **What Happens:**
    1. Upload your video
    2. App analyzes video type (portrait/landscape/square)
    3. Smart conversion based on original format
    4. Audio is trimmed and added
    5. Output optimized for mobile platforms
    
    **Best Results:**
    - Upload mobile/portrait videos as-is
    - For landscape videos, important content should be centered
    - Use high-quality source videos
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Smart Mobile Video Maker • Preserves mobile videos • Intelligent conversion • V25")

# ---------- CLEANUP ----------
import atexit

@atexit.register
def cleanup():
    """Clean up temp files"""
    try:
        files = [
            st.session_state.get('bg_path'),
            st.session_state.get('overlay_path'),
            st.session_state.get('last_output')
        ]
        for f in files:
            if f and os.path.exists(f):
                try:
                    os.unlink(f)
                except:
                    pass
    except:
        pass
