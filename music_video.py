import streamlit as st
import tempfile
import os
import gc
from PIL import Image, ImageFilter  # Added ImageFilter
import base64
import time
import numpy as np

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip
)

# Update version for any change
my_title = "🎬 Mobile Video Maker V 23"

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
        /* Main container */
        .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        /* Title and headers */
        h1 {
            font-size: 1.8rem !important;
            margin-bottom: 0.5rem !important;
        }
        
        h2, h3 {
            font-size: 1.4rem !important;
        }
        
        /* File uploader */
        .stFileUploader {
            font-size: 14px;
        }
        
        .stFileUploader > label {
            font-size: 14px !important;
        }
        
        /* Sliders */
        .stSlider {
            padding: 0.5rem 0;
        }
        
        .stSlider p {
            font-size: 14px;
            margin-bottom: 0.3rem;
        }
        
        /* Buttons */
        .stButton > button {
            width: 100% !important;
            margin: 0.5rem 0;
            padding: 0.75rem;
            font-size: 16px;
            min-height: 44px;
        }
        
        /* Columns */
        .stColumn {
            padding: 0.5rem;
        }
        
        /* Video player */
        video {
            max-width: 100% !important;
            height: auto !important;
        }
        
        /* Metrics */
        .stMetric {
            padding: 0.5rem;
        }
        
        .stMetric label {
            font-size: 12px !important;
        }
        
        .stMetric div {
            font-size: 16px !important;
        }
        
        /* Expandable sections */
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
    
    /* Prevent horizontal scrolling */
    div[data-testid="stVerticalBlock"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    
    /* Better touch targets for all devices */
    .stButton > button, .stDownloadButton > button {
        min-height: 44px;
        touch-action: manipulation;
    }
    
    /* Loading spinner optimization */
    .stSpinner > div {
        margin: 1rem auto;
    }
    
    /* Hide decorative elements on mobile */
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
    'target_resolution': (1080, 1920)  # Portrait 9:16 for mobile
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- PORTRAIT VIDEO SETTINGS ----------
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
PORTRAIT_RESOLUTION = (PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
ASPECT_RATIO = 9/16  # Portrait mobile

# ---------- MOBILE DETECTION ----------
def detect_mobile():
    """Detect if user is on mobile device"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        if ctx:
            user_agent = ctx.request.headers.get('User-Agent', '').lower()
            mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'tablet']
            return any(keyword in user_agent for keyword in mobile_keywords)
    except:
        pass
    return False

# Update mobile detection
st.session_state.mobile_view = detect_mobile()

# ---------- MOBILE-OPTIMIZED HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    try:
        # Check file size (limit to 500MB for mobile)
        max_size_mb = 500
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)
        
        if file_size > max_size_mb:
            st.error(f"File too large ({file_size:.1f}MB). Maximum size is {max_size_mb}MB for mobile devices.")
            return None
            
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
    """Show a single frame from video"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if clip.duration == 0:
            clip.close()
            return None
            
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Create portrait preview
        preview_width = 200
        preview_height = int(preview_width * (16/9))  # Calculate height for 9:16
        
        # FIXED: Use Resampling.LANCZOS instead of ANTIALIAS
        img = img.resize((preview_width, preview_height), Image.Resampling.LANCZOS)
        
        clip.close()
        return img
    except Exception as e:
        st.warning(f"Preview unavailable: {str(e)}")
        return None

def resize_for_portrait(clip):
    """Resize video clip to fit portrait mobile dimensions without black bars"""
    try:
        original_width, original_height = clip.size
        target_width, target_height = PORTRAIT_RESOLUTION
        
        # Calculate scaling to fill portrait frame
        scale_width = target_width / original_width
        scale_height = target_height / original_height
        
        # Use the larger scale to fill the frame (no black bars)
        scale = max(scale_width, scale_height)
        
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Resize the clip
        resized_clip = clip.resize((new_width, new_height))
        
        # Calculate crop to get exact portrait dimensions
        crop_x = (new_width - target_width) // 2
        crop_y = (new_height - target_height) // 2
        
        # Crop to portrait dimensions
        cropped_clip = resized_clip.crop(
            x1=crop_x,
            y1=crop_y,
            x2=crop_x + target_width,
            y2=crop_y + target_height
        )
        
        return cropped_clip
        
    except Exception as e:
        st.error(f"Error resizing for portrait: {str(e)}")
        return clip  # Return original if resize fails

def fit_content_to_portrait(clip):
    """Alternative method: Fit content within portrait frame with blur background"""
    try:
        original_width, original_height = clip.size
        target_width, target_height = PORTRAIT_RESOLUTION
        
        # Calculate scale to fit within portrait (maintain aspect ratio)
        scale_width = target_width / original_width
        scale_height = target_height / original_height
        
        # Use the smaller scale to fit content (no cropping)
        scale = min(scale_width, scale_height)
        
        new_width = int(original_width * scale)
        new_height = int(original_height * scale)
        
        # Resize the clip
        resized_clip = clip.resize((new_width, new_height))
        
        # Calculate position to center
        x_pos = (target_width - new_width) // 2
        y_pos = (target_height - new_height) // 2
        
        # Create blurred background version of the clip
        bg_clip = clip.resize((target_width, target_height))
        
        # Apply blur using numpy and PIL
        def apply_blur(frame):
            """Apply Gaussian blur to frame"""
            # Convert numpy array to PIL Image
            img = Image.fromarray(frame)
            # Apply blur
            blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
            # Convert back to numpy array
            return np.array(blurred)
        
        # Apply blur function to each frame
        bg_clip = bg_clip.fl_image(apply_blur)
        
        # Composite resized clip over blurred background
        final_clip = CompositeVideoClip([
            bg_clip,
            resized_clip.set_position((x_pos, y_pos))
        ])
        
        return final_clip.set_duration(clip.duration)
        
    except Exception as e:
        st.error(f"Error fitting content: {str(e)}")
        return clip

def create_portrait_video(original_clip, fit_method='crop'):
    """Create portrait mobile video from any aspect ratio"""
    try:
        if fit_method == 'crop':
            return resize_for_portrait(original_clip)
        else:  # 'fit'
            return fit_content_to_portrait(original_clip)
    except Exception as e:
        st.error(f"Error creating portrait video: {str(e)}")
        return original_clip

# ---------- MOBILE-FRIENDLY UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")

# Display target resolution info
st.info(f"🎯 **Target Output:** {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} (9:16 Portrait Mobile)")

# Use different layout for mobile vs desktop
if st.session_state.mobile_view:
    # Single column for mobile
    st.markdown("### Background Audio/Video")
    background_file = st.file_uploader(
        "Choose background file (MP3, MP4, MOV, M4A)",
        type=["mp3", "mp4", "mov", "m4a"],
        help="Audio will be extracted from this file",
        label_visibility="collapsed",
        key="bg_mobile"
    )
    
    st.markdown("---")
    st.markdown("### Overlay Video")
    overlay_file = st.file_uploader(
        "Choose overlay video (MP4, MOV)",
        type=["mp4", "mov"],
        help="Video will be converted to portrait 9:16",
        label_visibility="collapsed",
        key="overlay_mobile"
    )
else:
    # Two columns for desktop
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
            help="Video will be converted to portrait 9:16"
        )

# ---------- FIT METHOD SELECTION ----------
st.subheader("📐 Portrait Conversion Method")
fit_method = st.radio(
    "Choose how to fit your video to portrait:",
    options=['Crop to Fill (No black bars)', 'Fit with Blur Background'],
    index=0,
    horizontal=not st.session_state.mobile_view,
    help="Crop: Fills screen completely | Fit: Shows full video with blurred edges"
)

# Map selection to method parameter
fit_method_param = 'crop' if fit_method == 'Crop to Fill (No black bars)' else 'fit'

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
    
    with st.spinner("Loading background..." if not st.session_state.mobile_view else "📥 Loading..."):
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
                        emoji = "📹" if st.session_state.mobile_view else "✅"
                        st.success(f"{emoji} Video loaded: {st.session_state.bg_duration:.1f}s")
                    else:
                        st.error("⚠️ No audio in video")
                        st.session_state.bg_clip = None
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                    emoji = "🎵" if st.session_state.mobile_view else "✅"
                    st.success(f"{emoji} Audio loaded: {st.session_state.bg_duration:.1f}s")
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)[:100]}...")

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
    
    with st.spinner("Loading overlay..." if not st.session_state.mobile_view else "📥 Loading video..."):
        overlay_path = save_uploaded_file(overlay_file)
        if overlay_path:
            st.session_state.overlay_path = overlay_path
            st.session_state.overlay_is_image = False
            
            try:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                # Show original dimensions
                orig_width, orig_height = st.session_state.overlay_clip.size
                st.info(f"Original: {orig_width}×{orig_height} → Will convert to: {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    caption = "Portrait Preview" if st.session_state.mobile_view else "Portrait Preview (9:16)"
                    st.image(preview_img, caption=caption, use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ Error: {str(e)[:100]}...")

# ---------- MOBILE-FRIENDLY TRIM SLIDERS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    # Mobile-optimized audio trim
    st.markdown("**Audio**" if st.session_state.mobile_view else "**Audio Duration**")
    
    step_size = 0.1 if st.session_state.bg_duration < 60 else 0.5
    
    col1, col2 = st.columns(2)
    with col1:
        audio_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            0.0,
            step_size,
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
            step_size,
            key="audio_duration"
        )
    
    audio_end = audio_start + audio_duration
    duration_text = f"{audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)"
    st.success(f"🎵 Audio: {duration_text}")

if st.session_state.overlay_duration > 0:
    st.markdown("**Overlay Video**" if st.session_state.mobile_view else "**Overlay Video Trim**")
    
    step_size = 0.1 if st.session_state.overlay_duration < 60 else 0.5
    
    col1, col2 = st.columns(2)
    with col1:
        overlay_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.overlay_duration),
            0.0,
            step_size,
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
            step_size,
            key="overlay_duration"
        )
    
    overlay_end = overlay_start + overlay_duration
    duration_text = f"{overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s)"
    st.success(f"📹 Overlay: {duration_text}")

# ---------- MOBILE-OPTIMIZED PROCESS FUNCTION (ALWAYS PORTRAIT) ----------
def process_portrait_video():
    """Combine audio and video, ALWAYS output portrait mobile dimensions"""
    try:
        # Set processing flag
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
        
        # Progress tracking
        progress_bar = st.progress(0, text="Starting processing...")
        time.sleep(0.1)
        
        # Extract audio
        progress_bar.progress(10, text="Extracting audio...")
        if st.session_state.bg_is_video and st.session_state.bg_clip:
            audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video - trim first
        progress_bar.progress(30, text="Trimming overlay...")
        overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
        
        # Match durations
        progress_bar.progress(40, text="Matching durations...")
        if overlay.duration < final_audio_duration:
            loops_needed = int(final_audio_duration / overlay.duration) + 1
            overlay_loops = [overlay] * loops_needed
            overlay = concatenate_videoclips(overlay_loops)
            overlay = overlay.subclip(0, final_audio_duration)
        elif overlay.duration > final_audio_duration:
            overlay = overlay.subclip(0, final_audio_duration)
        
        # Convert to portrait mobile dimensions
        progress_bar.progress(60, text=f"Converting to portrait {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}...")
        portrait_overlay = create_portrait_video(overlay, fit_method_param)
        
        # Add audio to portrait video
        progress_bar.progress(80, text="Adding audio...")
        final_video = portrait_overlay.set_audio(audio_clip)
        final_video = final_video.set_duration(final_audio_duration)
        
        # Save video
        progress_bar.progress(90, text="Encoding video...")
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_portrait.mp4").name
        
        # Get actual dimensions after conversion
        final_width, final_height = portrait_overlay.size
        
        # Optimized encoding for mobile
        fps = 30  # Standard for mobile
        bitrate = "8M"  # Good quality for portrait
        
        final_video.write_videofile(
            output_path,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            bitrate=bitrate,
            verbose=False,
            logger=None,
            preset='medium',
            ffmpeg_params=[
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',  # Better mobile compatibility
                '-profile:v', 'high',
                '-level', '4.2'
            ]
        )
        
        progress_bar.progress(100, text="Complete!")
        time.sleep(0.5)
        progress_bar.empty()
        
        # Cleanup clips
        audio_clip.close()
        overlay.close()
        portrait_overlay.close()
        final_video.close()
        
        # Store output
        st.session_state.last_output = output_path
        
        return output_path, final_audio_duration, final_width, final_height
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0
    finally:
        st.session_state.processing = False

# ---------- CREATE BUTTON ----------
st.divider()

# Check if both files are uploaded
files_ready = st.session_state.bg_path and st.session_state.overlay_path

# Create button
create_disabled = not files_ready or st.session_state.processing
button_text = "⏳ Processing..." if st.session_state.processing else f"🎬 Create {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait Video"

if st.button(
    button_text,
    type="primary",
    disabled=create_disabled,
    use_container_width=True,
    key="create_button"
):
    if not files_ready:
        st.warning("Please upload both files first")
        st.stop()
    
    # Show conversion info
    orig_width, orig_height = st.session_state.overlay_clip.size
    st.info(f"🔄 Converting from {orig_width}×{orig_height} to {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} portrait...")
    
    # Process video
    output_path, duration, width, height = process_portrait_video()
    
    if output_path and os.path.exists(output_path):
        st.balloons()
        st.success(f"✅ Portrait mobile video created successfully!")
        
        # Show video
        st.subheader("📱 Your Portrait Mobile Video")
        
        # Display video with controls
        try:
            with open(output_path, "rb") as video_file:
                video_bytes = video_file.read()
            st.video(video_bytes, format="video/mp4")
        except Exception as e:
            st.info("Video preview available - use download button below")
        
        # Show video info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        # Display info in columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Aspect", "9:16")
        with col4:
            st.metric("Size", f"{file_size:.1f}MB")
        
        # Download button
        with open(output_path, "rb") as f:
            video_data = f.read()
            
            # Generate filename with resolution
            filename = f"mobile_portrait_{PORTRAIT_WIDTH}x{PORTRAIT_HEIGHT}.mp4"
            
            st.download_button(
                "📥 Download Portrait Video",
                video_data,
                file_name=filename,
                mime="video/mp4",
                type="primary",
                use_container_width=True,
                help=f"Download {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} portrait video for mobile"
            )
        
        # Mobile tips
        if st.session_state.mobile_view:
            st.caption("📱 **Mobile Tips:** This video is optimized for Instagram Reels, TikTok, and Stories")
        
        # Cleanup
        try:
            if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
                os.unlink(st.session_state.bg_path)
            if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
                os.unlink(st.session_state.overlay_path)
        except:
            pass
        
        # Clear session clips
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

# ---------- PORTRAIT VIDEO GUIDE ----------
with st.expander("📱 Portrait Mobile Video Guide", expanded=True):
    st.markdown(f"""
    ### Always Creates {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait Videos
    
    **This app automatically converts ALL videos to mobile-optimized portrait format.**
    
    ### 📐 **Conversion Methods:**
    
    1. **Crop to Fill (Recommended)**
       - Fills entire {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} frame
       - No black bars
       - May crop edges of your video
       - Best for: Instagram Reels, TikTok
    
    2. **Fit with Blur Background**
       - Shows full video without cropping
       - Adds blurred background to fill empty space
       - Best for: Presentations, tutorials
    
    ### 📱 **Mobile Platform Optimizations:**
    
    **Instagram Reels / TikTok:**
    - Perfect {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} format
    - High quality encoding
    - Fast loading
    
    **YouTube Shorts:**
    - 9:16 aspect ratio
    - Vertical video optimized
    - Mobile-first design
    
    **Stories (Instagram/Facebook):**
    - Full-screen vertical video
    - No cropping needed
    - Ready to share
    
    ### ⚙️ **Technical Specifications:**
    - **Resolution:** {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} pixels
    - **Aspect Ratio:** 9:16 (perfect portrait)
    - **Format:** MP4 (H.264 + AAC)
    - **FPS:** 30 (smooth playback)
    - **Bitrate:** 8 Mbps (high quality)
    
    ### 💡 **Tips for Best Results:**
    1. **Original should be at least 1080p** for best quality
    2. **Use well-lit videos** for better results
    3. **Keep important content centered** (edges may be cropped)
    4. **For talking heads:** Position in center 1/3 of frame
    5. **For landscape videos:** Choose "Fit with Blur Background"
    
    ### 🔄 **What Happens to Your Video:**
    1. Upload any video (landscape, square, or portrait)
    2. App automatically converts to {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}
    3. Content is fitted using your chosen method
    4. Audio is synced and trimmed
    5. Output is ready for mobile platforms
    """)

# ---------- COMPATIBILITY INFO ----------
st.divider()
st.caption(f"🎯 **Output:** Always {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait • 📱 Mobile-Optimized • 🚀 Fast Processing • V23")

# ---------- ADDITIONAL MOBILE OPTIMIZATIONS ----------
if st.session_state.mobile_view:
    st.markdown("""
    <script>
    // Mobile-specific optimizations
    document.addEventListener('DOMContentLoaded', function() {
        // Force portrait orientation for video playback
        const videos = document.querySelectorAll('video');
        videos.forEach(video => {
            video.setAttribute('playsinline', '');
            video.setAttribute('webkit-playsinline', '');
            video.setAttribute('x5-playsinline', '');
            video.setAttribute('x5-video-player-type', 'h5');
            video.setAttribute('x5-video-player-fullscreen', 'false');
        });
        
        // Prevent default video controls on mobile (Streamlit's are better)
        document.addEventListener('touchstart', function(e) {
            if (e.target.tagName === 'VIDEO' && e.touches.length > 1) {
                e.preventDefault();
            }
        }, { passive: false });
    });
    </script>
    """, unsafe_allow_html=True)

# ---------- CLEANUP FUNCTION ----------
import atexit

def cleanup_on_exit():
    """Clean up temporary files on exit"""
    try:
        files_to_remove = [
            st.session_state.get('bg_path'),
            st.session_state.get('overlay_path'),
            st.session_state.get('last_output')
        ]
        
        for file_path in files_to_remove:
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except:
                    pass
    except:
        pass

atexit.register(cleanup_on_exit)
