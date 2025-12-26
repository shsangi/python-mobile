import streamlit as st
import tempfile
import os
import gc
import time
import numpy as np
from PIL import Image, ImageFilter
import warnings
warnings.filterwarnings('ignore')

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip
)

# Update version for any change
my_title = "🎬 Mobile Video Maker V 24"

# ---------- MOBILE-FRIENDLY PAGE CONFIG ----------
st.set_page_config(
    page_title=my_title,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# ---------- MOBILE-OPTIMIZED CSS ----------
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Mobile viewport optimization */
    @media only screen and (max-width: 768px) {
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        h2, h3 {
            font-size: 1.4rem !important;
        }
        
        .stFileUploader {
            font-size: 14px;
        }
        
        .stFileUploader > label {
            font-size: 14px !important;
        }
        
        .stSlider {
            padding: 0.5rem 0;
        }
        
        .stSlider p {
            font-size: 14px;
            margin-bottom: 0.3rem;
        }
        
        .stButton > button {
            width: 100% !important;
            margin: 0.5rem 0;
            padding: 0.75rem;
            font-size: 16px;
            min-height: 44px;
        }
        
        .stColumn {
            padding: 0.5rem;
        }
        
        video {
            max-width: 100% !important;
            height: auto !important;
        }
        
        .stMetric {
            padding: 0.5rem;
        }
        
        .stMetric label {
            font-size: 12px !important;
        }
        
        .stMetric div {
            font-size: 16px !important;
        }
        
        .streamlit-expanderHeader {
            font-size: 14px !important;
            padding: 0.75rem 1rem;
        }
    }
    
    /* General mobile optimizations */
    .stApp {
        max-width: 100vw;
        overflow-x: hidden;
    }
    
    div[data-testid="stVerticalBlock"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .stButton > button, .stDownloadButton > button {
        min-height: 44px;
        touch-action: manipulation;
    }
    
    .stSpinner > div {
        margin: 1rem auto;
    }
    
    @media (max-width: 480px) {
        .stCaption {
            font-size: 12px;
        }
        
        .stAlert {
            padding: 0.75rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("📱 Always creates 9:16 portrait mobile videos")

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
    'mobile_view': False,
    'processing': False,
    'last_output': None,
    'target_resolution': (1080, 1920)
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- PORTRAIT VIDEO SETTINGS ----------
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
PORTRAIT_RESOLUTION = (PORTRAIT_WIDTH, PORTRAIT_HEIGHT)

# ---------- FIXED HELPER FUNCTIONS ----------
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

def show_single_frame_preview(video_path, time_point=1):
    """Show a single portrait preview frame"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if clip.duration == 0:
            clip.close()
            return None
            
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Create portrait preview (200x355 = 9:16)
        preview_width = 200
        preview_height = 355
        
        # Use correct PIL resize method
        img = img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        
        clip.close()
        return img
    except Exception as e:
        return None

def create_portrait_video(clip, method='crop'):
    """Convert any video to portrait 9:16 format"""
    try:
        original_width, original_height = clip.size
        target_width, target_height = PORTRAIT_RESOLUTION
        
        if method == 'crop':
            # Method 1: Crop to fill (no black bars)
            # Calculate scale to fill portrait frame
            scale_width = target_width / original_width
            scale_height = target_height / original_height
            
            # Use larger scale to fill frame completely
            scale = max(scale_width, scale_height)
            
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            # Resize
            resized_clip = clip.resize((new_width, new_height))
            
            # Calculate crop position (center)
            crop_x = (new_width - target_width) // 2
            crop_y = (new_height - target_height) // 2
            
            # Crop to target resolution
            portrait_clip = resized_clip.crop(
                x1=crop_x,
                y1=crop_y,
                x2=crop_x + target_width,
                y2=crop_y + target_height
            )
            
            return portrait_clip
            
        else:
            # Method 2: Fit with blur background
            # Calculate scale to fit within portrait
            scale_width = target_width / original_width
            scale_height = target_height / original_height
            scale = min(scale_width, scale_height)
            
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            # Resize main video
            resized_clip = clip.resize((new_width, new_height))
            
            # Create position for centering
            x_pos = (target_width - new_width) // 2
            y_pos = (target_height - new_height) // 2
            
            # Create background (blurred version of original)
            # For blur background, we'll create a solid color instead to avoid PIL dependency
            from moviepy.editor import ColorClip
            bg_clip = ColorClip(
                size=PORTRAIT_RESOLUTION,
                color=(30, 30, 30),  # Dark gray background
                duration=clip.duration
            )
            
            # Composite video over background
            final_clip = CompositeVideoClip([
                bg_clip,
                resized_clip.set_position((x_pos, y_pos))
            ])
            
            return final_clip.set_duration(clip.duration)
            
    except Exception as e:
        st.error(f"Portrait conversion error: {str(e)}")
        # Fallback: simple resize to portrait
        return clip.resize(PORTRAIT_RESOLUTION)

# ---------- UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")
st.info(f"🎯 **Target Output:** {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} (9:16 Portrait)")

# Layout
if st.session_state.mobile_view:
    st.markdown("### Background Audio/Video")
    background_file = st.file_uploader(
        "Choose background file",
        type=["mp3", "mp4", "mov", "m4a"],
        label_visibility="collapsed",
        key="bg_mobile"
    )
    
    st.markdown("---")
    st.markdown("### Overlay Video")
    overlay_file = st.file_uploader(
        "Choose overlay video",
        type=["mp4", "mov"],
        label_visibility="collapsed",
        key="overlay_mobile"
    )
else:
    col1, col2 = st.columns(2)
    
    with col1:
        background_file = st.file_uploader(
            "Background Audio/Video",
            type=["mp3", "mp4", "mov", "m4a"],
            help="Audio will be extracted"
        )
    
    with col2:
        overlay_file = st.file_uploader(
            "Overlay Video",
            type=["mp4", "mov"],
            help="Will be converted to portrait"
        )

# ---------- PORTRAIT METHOD SELECTION ----------
st.subheader("📐 Portrait Conversion")
fit_method = st.radio(
    "Choose conversion method:",
    options=['Crop to Fill (Recommended)', 'Fit with Background'],
    index=0,
    horizontal=not st.session_state.mobile_view,
    help="Crop: Fills screen | Fit: Shows full video with background"
)

fit_method_param = 'crop' if fit_method == 'Crop to Fill (Recommended)' else 'fit'

# ---------- BACKGROUND FILE HANDLING ----------
if background_file:
    if st.session_state.prev_bg_file != background_file.name:
        if st.session_state.bg_clip:
            try:
                st.session_state.bg_clip.close()
            except:
                pass
        st.session_state.bg_clip = None
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
                        st.error("No audio in video")
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                    st.success(f"✅ Audio loaded: {st.session_state.bg_duration:.1f}s")
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- OVERLAY FILE HANDLING ----------
if overlay_file:
    if st.session_state.prev_overlay_file != overlay_file.name:
        if st.session_state.overlay_clip:
            try:
                st.session_state.overlay_clip.close()
            except:
                pass
        st.session_state.overlay_clip = None
        st.session_state.prev_overlay_file = overlay_file.name
    
    with st.spinner("Loading overlay..."):
        overlay_path = save_uploaded_file(overlay_file)
        if overlay_path:
            st.session_state.overlay_path = overlay_path
            
            try:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                # Show original dimensions
                orig_width, orig_height = st.session_state.overlay_clip.size
                st.info(f"Original: {orig_width}×{orig_height} → Will convert to: {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Portrait Preview (9:16)", use_container_width=True)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Audio")
    
    col1, col2 = st.columns(2)
    with col1:
        audio_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            0.0,
            0.5,
            key="audio_start"
        )
    
    with col2:
        max_audio_duration = st.session_state.bg_duration - audio_start
        default_duration = min(60.0, float(max_audio_duration))
        
        audio_duration = st.slider(
            "Duration (seconds)",
            1.0,
            float(max_audio_duration),
            default_duration,
            0.5,
            key="audio_duration"
        )
    
    audio_end = audio_start + audio_duration
    st.success(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)")

if st.session_state.overlay_duration > 0:
    st.subheader("✂️ Trim Video")
    
    col1, col2 = st.columns(2)
    with col1:
        overlay_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.overlay_duration),
            0.0,
            0.5,
            key="overlay_start"
        )
    
    with col2:
        max_overlay_duration = st.session_state.overlay_duration - overlay_start
        default_duration = min(60.0, float(max_overlay_duration))
        
        overlay_duration = st.slider(
            "Duration (seconds)",
            1.0,
            float(max_overlay_duration),
            default_duration,
            0.5,
            key="overlay_duration"
        )
    
    overlay_end = overlay_start + overlay_duration
    st.success(f"📹 Video: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s)")

# ---------- MAIN PROCESSING FUNCTION ----------
def create_final_portrait_video():
    """Create portrait mobile video"""
    try:
        st.session_state.processing = True
        
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 
                                                 min(60, st.session_state.bg_duration))
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration',
                                                   min(60, st.session_state.overlay_duration))
        overlay_end = overlay_start + overlay_duration_val
        
        # Progress
        progress_bar = st.progress(0, text="Starting...")
        time.sleep(0.1)
        
        # Extract audio
        progress_bar.progress(20, text="Extracting audio...")
        if st.session_state.bg_is_video and st.session_state.bg_clip:
            audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Trim overlay
        progress_bar.progress(40, text="Trimming video...")
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
        
        # Convert to portrait
        progress_bar.progress(80, text=f"Converting to {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}...")
        portrait_video = create_portrait_video(overlay, fit_method_param)
        
        # Add audio
        final_video = portrait_video.set_audio(audio_clip)
        final_video = final_video.set_duration(final_audio_duration)
        
        # Save
        progress_bar.progress(90, text="Saving video...")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_portrait.mp4").name
        
        # Get final dimensions
        final_width, final_height = portrait_video.size
        
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
        portrait_video.close()
        final_video.close()
        
        return output_path, final_audio_duration, final_width, final_height
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        return None, 0, 0, 0
    finally:
        st.session_state.processing = False

# ---------- CREATE BUTTON ----------
st.divider()

files_ready = st.session_state.bg_path and st.session_state.overlay_path
create_disabled = not files_ready or st.session_state.processing
button_text = "⏳ Processing..." if st.session_state.processing else f"🎬 Create {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Video"

if st.button(
    button_text,
    type="primary",
    disabled=create_disabled,
    use_container_width=True
):
    if not files_ready:
        st.warning("Upload both files first")
        st.stop()
    
    # Show conversion info
    orig_width, orig_height = st.session_state.overlay_clip.size
    st.info(f"Converting: {orig_width}×{orig_height} → {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}")
    
    # Process
    output_path, duration, width, height = create_final_portrait_video()
    
    if output_path and os.path.exists(output_path):
        st.balloons()
        st.success("✅ Portrait video created!")
        
        # Show video
        st.subheader("📱 Your Portrait Video")
        
        try:
            with open(output_path, "rb") as f:
                video_bytes = f.read()
            st.video(video_bytes)
        except:
            st.info("Video ready for download")
        
        # Info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Format", "9:16")
        with col4:
            st.metric("Size", f"{file_size:.1f}MB")
        
        # Download
        with open(output_path, "rb") as f:
            video_data = f.read()
            
            st.download_button(
                "📥 Download Portrait Video",
                video_data,
                file_name=f"portrait_{PORTRAIT_WIDTH}x{PORTRAIT_HEIGHT}.mp4",
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

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How It Works", expanded=True):
    st.markdown(f"""
    ### Always Creates {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait Videos
    
    **Input ANY video → Output perfect 9:16 mobile video**
    
    **Two Conversion Methods:**
    
    1. **Crop to Fill (Recommended)**
       - Fills entire screen
       - No black bars
       - Crops edges if needed
       - Best for social media
    
    2. **Fit with Background**
       - Shows full video
       - Adds background to fill space
       - Nothing cropped
       - Good for tutorials
    
    **Perfect For:**
    - Instagram Reels
    - TikTok Videos  
    - YouTube Shorts
    - Instagram/Facebook Stories
    - WhatsApp Status
    
    **Features:**
    - Automatic portrait conversion
    - Audio/video synchronization
    - Precise trimming controls
    - High-quality output
    - Mobile-optimized encoding
    
    **Steps:**
    1. Upload background audio/video
    2. Upload overlay video  
    3. Choose conversion method
    4. Trim audio and video
    5. Create and download
    
    **Note:** All videos output at {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} (9:16)
    """)

# ---------- FOOTER ----------
st.divider()
st.caption(f"🎯 Always {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait • 📱 Mobile First • 🚀 Version 24")

# ---------- CLEANUP ----------
import atexit

@atexit.register
def cleanup():
    """Clean temporary files on exit"""
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
