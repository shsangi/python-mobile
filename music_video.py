import streamlit as st
import tempfile
import os
import gc
from PIL import Image
import base64
import numpy as np

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip
)
my_title = "🎬 Mobile Video Maker V 2:1"
# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title= my_title,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide the sidebar and improve mobile display
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Mobile-friendly buttons */
    .stButton > button {
        width: 100%;
    }
    /* Better video display */
    .stVideo {
        border-radius: 10px;
        overflow: hidden;
        margin: 10px 0;
    }
    /* Responsive containers */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - Mobile optimized")

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
    'bg_video_width': None,
    'bg_video_height': None,
    'overlay_width': None,
    'overlay_height': None,
    'output_path': None
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- IMPROVED HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def show_single_frame_preview(video_path, time_point=1):
    """Show a single frame from video"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Maintain aspect ratio for preview
        img.thumbnail((400, 400))
        
        clip.close()
        return img
    except Exception as e:
        st.warning(f"Preview error: {str(e)}")
        return None

def get_video_info(video_path):
    """Get video dimensions and info"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        width, height = clip.size
        duration = clip.duration
        fps = clip.fps
        clip.close()
        return width, height, duration, fps
    except:
        return None, None, None, None

# ---------- UPLOAD SECTIONS ----------
st.subheader("Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a", "avi", "mkv"],
        help="Audio will be extracted from this file. For video backgrounds, first frame will be used."
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save and load
        with st.spinner("Loading background..."):
            st.session_state.bg_path = save_uploaded_file(background_file)
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi', '.mkv']
            
            try:
                if st.session_state.bg_is_video:
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    
                    # Get video dimensions
                    st.session_state.bg_video_width, st.session_state.bg_video_height = st.session_state.bg_clip.size
                    
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        st.success(f"✅ Video: {background_file.name}")
                        st.info(f"Size: {st.session_state.bg_video_width}×{st.session_state.bg_video_height} | Duration: {st.session_state.bg_duration:.1f}s")
                    else:
                        st.session_state.bg_duration = st.session_state.bg_clip.duration
                        st.warning("⚠️ No audio in video - using video duration")
                        st.info(f"Size: {st.session_state.bg_video_width}×{st.session_state.bg_video_height} | Duration: {st.session_state.bg_duration:.1f}s")
                    
                    # Show preview
                    preview_img = show_single_frame_preview(st.session_state.bg_path)
                    if preview_img:
                        st.image(preview_img, caption="Background preview", use_column_width=True)
                        
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    st.success(f"✅ Audio: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                    audio.close()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Video overlay (will not be resized). For mobile, use 9:16 aspect ratio."
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save and load
        with st.spinner("Loading overlay..."):
            st.session_state.overlay_path = save_uploaded_file(overlay_file)
            st.session_state.overlay_is_image = False
            
            try:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                st.session_state.overlay_width, st.session_state.overlay_height = st.session_state.overlay_clip.size
                
                st.success(f"✅ Overlay: {overlay_file.name}")
                st.info(f"Size: {st.session_state.overlay_width}×{st.session_state.overlay_height} | Duration: {st.session_state.overlay_duration:.1f}s")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Overlay preview", use_column_width=True)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- ENHANCED TRIM SLIDERS ----------
if st.session_state.bg_duration > 0:
    st.subheader("Trim Settings")
    
    # Audio trim section
    st.markdown("**Audio Duration**")
    audio_start = st.slider(
        "Audio Start (seconds)",
        0.0,
        float(st.session_state.bg_duration),
        0.0,
        0.5,
        key="audio_start"
    )
    
    # Calculate audio end based on start + duration
    max_audio_duration = st.session_state.bg_duration - audio_start
    audio_duration = st.slider(
        "Audio Duration (seconds)",
        1.0,
        float(max_audio_duration),
        min(30.0, float(max_audio_duration)),
        0.5,
        key="audio_duration"
    )
    
    audio_end = audio_start + audio_duration
    st.info(f"Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s total)")

if st.session_state.overlay_duration > 0:
    # Overlay trim section
    st.markdown("**Overlay Video Trim**")
    overlay_start = st.slider(
        "Overlay Start (seconds)",
        0.0,
        float(st.session_state.overlay_duration),
        0.0,
        0.5,
        key="overlay_start"
    )
    
    max_overlay_duration = st.session_state.overlay_duration - overlay_start
    overlay_duration = st.slider(
        "Overlay Duration (seconds)",
        1.0,
        float(max_overlay_duration),
        min(30.0, float(max_overlay_duration)),
        0.5,
        key="overlay_duration"
    )
    
    overlay_end = overlay_start + overlay_duration
    st.info(f"Overlay: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")
    
    # Display aspect ratio info
    if st.session_state.overlay_width and st.session_state.overlay_height:
        aspect_ratio = st.session_state.overlay_width / st.session_state.overlay_height
        if aspect_ratio < 0.8:
            st.success("📱 Portrait aspect ratio (mobile-friendly)")
        elif aspect_ratio > 1.2:
            st.info("🖥️ Landscape aspect ratio")
        else:
            st.info("⏺️ Square aspect ratio")

# ---------- PROCESS FUNCTION WITH BETTER MOBILE SUPPORT ----------
def process_video_mobile_friendly():
    """Combine audio and video with mobile optimization"""
    try:
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 30)
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration', 30)
        overlay_end = overlay_start + overlay_duration_val
        
        # Extract audio
        with st.spinner("Extracting audio..."):
            if st.session_state.bg_is_video and st.session_state.bg_clip.audio:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            elif st.session_state.bg_is_video:
                # If video has no audio, create silent audio
                from moviepy.audio.AudioClip import AudioClip
                audio_clip = AudioClip(lambda t: 0, duration=audio_duration_val)
            else:
                # Load audio file fresh
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video
        with st.spinner("Processing overlay video..."):
            # Trim overlay
            overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
            
            # Match durations - loop overlay if shorter than audio
            if overlay.duration < final_audio_duration:
                loops_needed = int(final_audio_duration / overlay.duration) + 1
                overlay_loops = [overlay] * loops_needed
                overlay = concatenate_videoclips(overlay_loops)
                overlay = overlay.subclip(0, final_audio_duration)
            elif overlay.duration > final_audio_duration:
                overlay = overlay.subclip(0, final_audio_duration)
            
            # Set audio to overlay
            final_video = overlay.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
        
        # Save video with mobile-friendly settings
        with st.spinner("Encoding video for mobile..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Get original dimensions
            width, height = overlay.size
            
            # Mobile-optimized encoding
            final_video.write_videofile(
                output_path,
                fps=overlay.fps,
                codec="libx264",
                audio_codec="aac",
                bitrate="5M",  # Lower bitrate for mobile
                verbose=False,
                logger=None,
                preset='fast',  # Faster encoding
                ffmpeg_params=[
                    '-movflags', '+faststart',  # For streaming
                    '-pix_fmt', 'yuv420p',  # Better mobile compatibility
                    '-profile:v', 'baseline',  # Wider device compatibility
                    '-level', '3.0'
                ]
            )
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        final_video.close()
        
        return output_path, final_audio_duration, width, height
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        import traceback
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0

# ---------- CREATE BUTTON ----------
st.divider()

# Check if both files are uploaded
files_ready = st.session_state.bg_path and st.session_state.overlay_path

if st.button("🎬 Create Final Video", 
             type="primary", 
             disabled=not files_ready,
             use_container_width=True):
    
    if not files_ready:
        st.warning("Please upload both background and overlay files first")
        st.stop()
    
    # Show processing animation
    with st.spinner("Creating your video... This may take a moment."):
        output_path, duration, width, height = process_video_mobile_friendly()
    
    if output_path and os.path.exists(output_path):
        st.success("✅ Video created successfully!")
        
        # Show video
        st.subheader("Your Video")
        
        try:
            # Display video with better controls
            video_file = open(output_path, 'rb')
            video_bytes = video_file.read()
            st.video(video_bytes, format="video/mp4", start_time=0)
            video_file.close()
        except Exception as e:
            st.warning(f"Preview not available: {str(e)}")
            st.info("Download the video to view it")
        
        # Show detailed info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Size", f"{file_size:.1f}MB")
        
        # Additional info
        if width and height:
            aspect_ratio = width / height
            if aspect_ratio < 0.8:
                st.success("✅ Mobile portrait format (9:16)")
            elif aspect_ratio > 1.2:
                st.info("🖥️ Desktop landscape format (16:9)")
        
        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "📥 Download Video",
                f,
                file_name=f"mobile_video_{width}x{height}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Store output path for later cleanup
        st.session_state.output_path = output_path
        
        # Show cleanup instructions
        st.info("💡 The video will be deleted when you refresh the page. Download it now to save.")

# ---------- CLEANUP ON REFRESH ----------
# Clean up old temp files
def cleanup_temp_files():
    """Clean up temporary files"""
    try:
        if st.session_state.output_path and os.path.exists(st.session_state.output_path):
            os.unlink(st.session_state.output_path)
        
        if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
            os.unlink(st.session_state.bg_path)
        
        if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
            os.unlink(st.session_state.overlay_path)
    except:
        pass

# Call cleanup
cleanup_temp_files()

# ---------- IMPROVED INSTRUCTIONS ----------
with st.expander("📖 How to Use - Mobile Optimized", expanded=True):
    st.markdown("""
    ### Mobile Video Creator
    
    **Perfect for social media videos (Instagram, TikTok, YouTube Shorts)**
    
    **What this does:**
    1. Extracts audio from background file (MP3/MP4)
    2. Uses overlay video as visual (MP4/MOV)
    3. Trims both audio and video independently
    4. Combines them **without resizing** (keeps original quality)
    5. Optimizes for mobile playback
    
    **Best Practices:**
    
    **For Mobile Videos (9:16 Portrait):**
    - Use overlay videos shot in portrait mode
    - Ideal resolution: 1080×1920 or 720×1280
    - File format: MP4 with H.264 codec
    
    **For Desktop Videos (16:9 Landscape):**
    - Use overlay videos shot in landscape mode
    - Ideal resolution: 1920×1080 or 1280×720
    
    **Steps:**
    1. **Upload Background** - Audio or video file
    2. **Upload Overlay** - Video file (will not be resized)
    3. **Trim Audio** - Select start and duration
    4. **Trim Video** - Select start and duration
    5. **Click Create** - Get your combined video
    
    **Note:** 
    - Videos maintain original size and aspect ratio
    - No black borders added
    - Mobile-optimized encoding for faster loading
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("🎥 Mobile Video Maker • No resizing • Original quality • Mobile optimized")
