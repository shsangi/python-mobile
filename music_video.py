import streamlit as st
import tempfile
import os
import gc
from PIL import Image
import base64

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Fullscreen Video Maker",
    layout="centered",
    initial_sidebar_state="collapsed"  # Hides the sidebar
)

# Hide the sidebar completely
st.markdown("""
<style>
    /* Hide the sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }
    
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
    }
</style>
""", unsafe_allow_html=True)

# ---------- VERSION ----------
VERSION = "2.4.1"
st.title(f"📱 Fullscreen Video Maker")
st.caption("Create videos with background music - Fit Entire mode")

# ---------- FIXED SCREEN SIZE ----------
# Using Instagram/TikTok vertical format (9:16)
SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 1920
FIT_MODE = "Fit Entire"  # Fixed to only this mode

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
if 'prev_bg_file' not in st.session_state:
    st.session_state.prev_bg_file = None
if 'prev_overlay_file' not in st.session_state:
    st.session_state.prev_overlay_file = None

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def generate_video_preview(video_path, start_time=0, end_time=None, height=200):
    """Generate preview for video"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        
        if end_time is None or end_time > clip.duration:
            end_time = min(clip.duration, start_time + 3)
        
        # Ensure valid time range
        start_time = max(0, min(start_time, clip.duration - 0.1))
        end_time = max(start_time + 0.1, min(end_time, clip.duration))
        
        # Extract single frame for preview (faster)
        frame_time = start_time + (end_time - start_time) / 2
        frame = clip.get_frame(frame_time)
        
        # Convert to PIL Image
        img = Image.fromarray(frame)
        img.thumbnail((height * 2, height))
        
        # Save as JPEG
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix="_preview.jpg")
        img.save(temp_img.name, "JPEG", quality=85)
        temp_img.close()
        
        clip.close()
        return temp_img.name
    except Exception as e:
        st.warning(f"Preview generation: {str(e)}")
        return None

def generate_image_preview(image_path, max_size=(300, 300)):
    """Generate preview for image"""
    try:
        img = Image.open(image_path)
        img.thumbnail(max_size)
        
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix="_preview.jpg")
        img.save(temp_img.name, "JPEG", quality=90)
        temp_img.close()
        
        return temp_img.name
    except Exception as e:
        st.error(f"Image preview error: {str(e)}")
        return None

def fix_dimension(value):
    """Ensure dimensions are integers (fixes the float error)"""
    return int(round(value))

# ---------- UPLOAD SECTIONS ----------
st.subheader("Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Music/Video",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov"],
        help="Upload audio or video file (audio will be used)"
    )
    
    if background_file:
        # Clear previous state if new file uploaded
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.bg_audio_clip = None
            st.session_state.bg_preview_path = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save file
        st.session_state.bg_path = save_uploaded_file(background_file)
        bg_ext = os.path.splitext(background_file.name)[1].lower()
        st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
        
        # Load the clip
        try:
            if st.session_state.bg_is_video:
                st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                st.session_state.bg_audio_clip = st.session_state.bg_clip.audio
                if st.session_state.bg_audio_clip is None:
                    st.error("No audio found in video!")
                    st.stop()
            else:
                st.session_state.bg_clip = None
                st.session_state.bg_audio_clip = AudioFileClip(st.session_state.bg_path)
            
            st.session_state.bg_duration = st.session_state.bg_audio_clip.duration
            
            # Generate preview if video
            if st.session_state.bg_is_video:
                preview_end = min(3, st.session_state.bg_duration)
                st.session_state.bg_preview_path = generate_video_preview(
                    st.session_state.bg_path, 
                    start_time=0, 
                    end_time=preview_end
                )
            
            st.success(f"✅ Loaded: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
            
        except Exception as e:
            st.error(f"Error loading background: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay (Image or Video)",
        type=["mp4", "mov", "png", "jpg", "jpeg", "webp"],
        help="Upload image or video overlay"
    )
    
    if overlay_file:
        # Clear previous state if new file uploaded
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.overlay_preview_path = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save file
        st.session_state.overlay_path = save_uploaded_file(overlay_file)
        overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
        st.session_state.overlay_is_image = overlay_ext in ['.png', '.jpg', '.jpeg', '.webp']
        
        # Load the clip
        try:
            if st.session_state.overlay_is_image:
                st.session_state.overlay_clip = None
                st.session_state.overlay_duration = 0
                st.session_state.overlay_preview_path = generate_image_preview(st.session_state.overlay_path)
            else:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                # Generate preview
                preview_end = min(3, st.session_state.overlay_duration)
                st.session_state.overlay_preview_path = generate_video_preview(
                    st.session_state.overlay_path,
                    start_time=0,
                    end_time=preview_end
                )
            
            st.success(f"✅ Loaded: {overlay_file.name}")
            
        except Exception as e:
            st.error(f"Error loading overlay: {str(e)}")

# ---------- DURATION SELECTION ----------
if st.session_state.bg_duration > 0:
    st.subheader("Duration Settings")
    
    # Audio duration selection
    audio_start = st.slider(
        "Audio Start Time (seconds)",
        0.0,
        st.session_state.bg_duration,
        0.0,
        0.1,
        key="audio_start"
    )
    
    audio_end = st.slider(
        "Audio End Time (seconds)",
        0.0,
        st.session_state.bg_duration,
        st.session_state.bg_duration,
        0.1,
        key="audio_end"
    )
    
    if audio_end <= audio_start:
        audio_end = min(audio_start + 1, st.session_state.bg_duration)
        st.warning(f"End time adjusted to {audio_end:.1f}s")
    
    audio_duration = audio_end - audio_start
    st.info(f"**Audio duration:** {audio_duration:.1f} seconds")
    
    # Overlay duration for videos
    if not st.session_state.overlay_is_image and st.session_state.overlay_duration > 0:
        overlay_start = st.slider(
            "Overlay Start Time (seconds)",
            0.0,
            st.session_state.overlay_duration,
            0.0,
            0.1,
            key="overlay_start"
        )
        
        overlay_end = st.slider(
            "Overlay End Time (seconds)",
            0.0,
            st.session_state.overlay_duration,
            st.session_state.overlay_duration,
            0.1,
            key="overlay_end"
        )
        
        if overlay_end <= overlay_start:
            overlay_end = min(overlay_start + 1, st.session_state.overlay_duration)
            st.warning(f"Overlay end time adjusted to {overlay_end:.1f}s")
        
        overlay_selected_duration = overlay_end - overlay_start
        st.info(f"**Overlay duration:** {overlay_selected_duration:.1f} seconds")

# ---------- PREVIEW ----------
if st.session_state.bg_preview_path or st.session_state.overlay_preview_path:
    st.subheader("Preview")
    preview_cols = st.columns(2)
    
    with preview_cols[0]:
        if st.session_state.bg_preview_path:
            caption = "Background Video" if st.session_state.bg_is_video else "Audio File"
            st.image(st.session_state.bg_preview_path, caption=caption, use_column_width=True)
    
    with preview_cols[1]:
        if st.session_state.overlay_preview_path:
            caption = "Image Overlay" if st.session_state.overlay_is_image else "Video Overlay"
            st.image(st.session_state.overlay_preview_path, caption=caption, use_column_width=True)

# ---------- PROCESS FUNCTION ----------
def process_fit_entire():
    """Process with Fit Entire mode (fixed)"""
    try:
        # Get audio selection
        audio_start = st.session_state.get('audio_start', 0)
        audio_end = st.session_state.get('audio_end', st.session_state.bg_duration)
        
        # Extract audio
        audio_clip = st.session_state.bg_audio_clip.subclip(audio_start, audio_end)
        final_duration = audio_clip.duration
        
        # Process overlay
        if st.session_state.overlay_is_image:
            # Load image
            img = Image.open(st.session_state.overlay_path)
            img_width, img_height = img.size
            
            # Calculate dimensions for Fit Entire
            screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
            image_ratio = img_width / img_height
            
            # Fix: Ensure integer dimensions
            if image_ratio > screen_ratio:
                # Image is wider than screen - fit to width
                new_width = SCREEN_WIDTH
                new_height = fix_dimension(SCREEN_WIDTH / image_ratio)
            else:
                # Image is taller than screen - fit to height
                new_height = SCREEN_HEIGHT
                new_width = fix_dimension(SCREEN_HEIGHT * image_ratio)
            
            # Resize image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Create black background
            background = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
            
            # Calculate center position
            paste_x = (SCREEN_WIDTH - new_width) // 2
            paste_y = (SCREEN_HEIGHT - new_height) // 2
            
            # Paste centered
            background.paste(img, (paste_x, paste_y))
            
            # Save processed image
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            background.save(temp_img.name, "JPEG", quality=95)
            temp_img_path = temp_img.name
            
            # Create image clip
            overlay = ImageClip(temp_img_path, duration=final_duration)
            
        else:
            # Video overlay
            overlay_start = st.session_state.get('overlay_start', 0)
            overlay_end = st.session_state.get('overlay_end', st.session_state.overlay_duration)
            
            # Get overlay clip
            overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
            
            # Handle duration matching
            if overlay.duration < final_duration:
                # Loop video
                loops = int(final_duration // overlay.duration) + 1
                overlay_loops = [overlay] * loops
                overlay = concatenate_videoclips(overlay_loops)
                overlay = overlay.subclip(0, final_duration)
            elif overlay.duration > final_duration:
                overlay = overlay.subclip(0, final_duration)
            
            # Resize for Fit Entire
            orig_width, orig_height = overlay.size
            screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
            video_ratio = orig_width / orig_height
            
            # Fix: Ensure integer dimensions
            if video_ratio > screen_ratio:
                # Fit to width
                overlay = overlay.resize(width=SCREEN_WIDTH)
            else:
                # Fit to height
                overlay = overlay.resize(height=SCREEN_HEIGHT)
            
            # Get current dimensions after resize
            current_width, current_height = overlay.size
            
            # Create black background
            background = ColorClip(
                (SCREEN_WIDTH, SCREEN_HEIGHT), 
                color=(0, 0, 0), 
                duration=overlay.duration
            )
            
            # Calculate center position
            pos_x = (SCREEN_WIDTH - current_width) // 2
            pos_y = (SCREEN_HEIGHT - current_height) // 2
            
            # Create composite
            overlay = overlay.set_position((pos_x, pos_y))
            overlay = CompositeVideoClip(
                [background, overlay], 
                size=(SCREEN_WIDTH, SCREEN_HEIGHT)
            )
        
        # Add audio to overlay
        overlay = overlay.set_audio(audio_clip)
        final_video = overlay.set_duration(final_duration)
        final_video = final_video.set_fps(30)
        
        # Save video
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8M",
            verbose=False,
            logger=None,
            threads=2,
            preset='medium',
            ffmpeg_params=['-movflags', '+faststart']
        )
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        final_video.close()
        
        # Clean temp image file if created
        if 'temp_img_path' in locals():
            try:
                os.unlink(temp_img_path)
            except:
                pass
        
        return output_path, final_duration
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        import traceback
        with st.expander("Technical Details"):
            st.code(traceback.format_exc())
        return None, 0

# ---------- CREATE BUTTON ----------
st.divider()

create_disabled = not (st.session_state.bg_path and st.session_state.overlay_path)

if st.button("🎬 Create Video", 
             type="primary", 
             disabled=create_disabled,
             use_container_width=True):
    
    if create_disabled:
        st.warning("Please upload both files first")
        st.stop()
    
    with st.spinner("Creating your video..."):
        output_path, video_duration = process_fit_entire()
        
        if output_path and os.path.exists(output_path):
            st.success("✅ Video created successfully!")
            
            # Display video
            st.subheader("Your Video")
            
            # Video preview
            try:
                st.video(output_path)
            except:
                st.info("Video preview")
            
            # Video info
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            
            info_cols = st.columns(3)
            with info_cols[0]:
                st.metric("Duration", f"{video_duration:.1f}s")
            with info_cols[1]:
                st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
            with info_cols[2]:
                st.metric("Size", f"{file_size:.1f}MB")
            
            st.info(f"Fit mode: {FIT_MODE}")
            
            # Download button
            with open(output_path, "rb") as f:
                st.download_button(
                    "📥 Download Video",
                    f,
                    file_name=f"video_{SCREEN_WIDTH}x{SCREEN_HEIGHT}.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True
                )
            
            # Cleanup temp files
            cleanup_files = [
                st.session_state.bg_path,
                st.session_state.overlay_path,
                st.session_state.bg_preview_path,
                st.session_state.overlay_preview_path
            ]
            
            for file in cleanup_files:
                if file and os.path.exists(file):
                    try:
                        os.unlink(file)
                    except:
                        pass
            
            # Clear session state
            for key in list(st.session_state.keys()):
                if key not in ['prev_bg_file', 'prev_overlay_file']:
                    st.session_state[key] = None
            
            # Force garbage collection
            gc.collect()

# ---------- INSTRUCTIONS ----------
with st.expander("How to Use", expanded=True):
    st.markdown(f"""
    ### Simple Video Creator
    
    1. **Upload Files**:
       - **Background**: Audio or video file (MP3, MP4, MOV)
       - **Overlay**: Image or video file (PNG, JPG, MP4)
    
    2. **Select Duration**:
       - Choose start and end times for audio
       - For video overlays, select clip segment
    
    3. **Create Video**:
       - Click "Create Video" button
       - Overlay will be **centered with black borders**
       - Output: {SCREEN_WIDTH}×{SCREEN_HEIGHT} vertical video
    
    **Note**: This app only uses "Fit Entire" mode - your content will be shown completely with black borders if needed.
    """)

# ---------- FOOTER ----------
st.divider()
st.caption(f"v{VERSION} • Fit Entire mode only • {SCREEN_WIDTH}×{SCREEN_HEIGHT}")
