import streamlit as st
import tempfile
import os
import gc
import subprocess
from PIL import Image
import numpy as np

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips
)
from moviepy.config import change_settings

# Fix FFMPEG path issues (important for Streamlit Cloud)
import warnings
warnings.filterwarnings("ignore")

my_title = "🎬 Mobile Video Maker V 22"

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title=my_title,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide the sidebar and improve mobile styling
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Mobile-friendly buttons */
    .stButton > button {
        width: 100%;
    }
    /* Video container styling */
    .stVideo {
        background-color: #000;
        border-radius: 10px;
        padding: 10px;
    }
    /* Fix for video display */
    video {
        max-width: 100% !important;
        height: auto !important;
        object-fit: contain !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - No resizing")

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
    'bg_loaded': False,
    'overlay_loaded': False
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- IMPROVED HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location with proper extension"""
    ext = os.path.splitext(uploaded_file.name)[1]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def get_video_info(video_path):
    """Get video information using ffprobe"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,codec_name,duration',
            '-of', 'json',
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            import json
            info = json.loads(result.stdout)
            return info
    except:
        return None
    return None

def validate_video_file(file_path):
    """Check if video file is valid"""
    try:
        clip = VideoFileClip(file_path, audio=False)
        duration = clip.duration
        width, height = clip.size
        clip.close()
        return True, duration, width, height
    except Exception as e:
        return False, 0, 0, 0

def show_single_frame_preview(video_path, time_point=1):
    """Show a single frame from video with error handling"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if clip.duration <= 0:
            return None
        
        if time_point > clip.duration:
            time_point = max(0, clip.duration / 2)
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Maintain aspect ratio for preview
        max_size = (300, 300)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        clip.close()
        return img
    except Exception as e:
        print(f"Preview error: {e}")
        return None

def cleanup_old_files():
    """Cleanup old temporary files"""
    if 'bg_path' in st.session_state and st.session_state.bg_path:
        if os.path.exists(st.session_state.bg_path):
            try:
                os.unlink(st.session_state.bg_path)
            except:
                pass
    
    if 'overlay_path' in st.session_state and st.session_state.overlay_path:
        if os.path.exists(st.session_state.overlay_path):
            try:
                os.unlink(st.session_state.overlay_path)
            except:
                pass

# ---------- UPLOAD SECTIONS ----------
st.subheader("Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a", "wav", "avi", "mkv"],
        help="Audio will be extracted from this file. Supported: MP3, MP4, MOV, M4A"
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name or not st.session_state.bg_loaded:
            # Cleanup old files
            if st.session_state.bg_clip:
                try:
                    st.session_state.bg_clip.close()
                except:
                    pass
            
            st.session_state.bg_loaded = False
            st.session_state.prev_bg_file = background_file.name
            
            # Save and load
            with st.spinner("Loading background..."):
                cleanup_old_files()  # Clean old files first
                st.session_state.bg_path = save_uploaded_file(background_file)
                bg_ext = os.path.splitext(background_file.name)[1].lower()
                st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi', '.mkv']
                
                try:
                    if st.session_state.bg_is_video:
                        # Load video with audio
                        st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                        if st.session_state.bg_clip.audio is not None:
                            st.session_state.bg_duration = st.session_state.bg_clip.audio.duration
                        else:
                            st.session_state.bg_duration = st.session_state.bg_clip.duration
                        
                        st.success(f"✅ Video: {background_file.name}")
                        st.info(f"Duration: {st.session_state.bg_duration:.1f}s")
                        
                        # Show video info
                        width, height = st.session_state.bg_clip.size
                        st.caption(f"Resolution: {width}×{height}")
                    else:
                        # Load audio only
                        audio_clip = AudioFileClip(st.session_state.bg_path)
                        st.session_state.bg_duration = audio_clip.duration
                        audio_clip.close()
                        st.success(f"✅ Audio: {background_file.name}")
                        st.info(f"Duration: {st.session_state.bg_duration:.1f}s")
                    
                    st.session_state.bg_loaded = True
                    
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
                    st.info("Try converting to MP4 format for better compatibility")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        help="Video overlay (will not be resized). For best results, use MP4 format."
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name or not st.session_state.overlay_loaded:
            # Cleanup old files
            if st.session_state.overlay_clip:
                try:
                    st.session_state.overlay_clip.close()
                except:
                    pass
            
            st.session_state.overlay_loaded = False
            st.session_state.prev_overlay_file = overlay_file.name
            
            # Save and load
            with st.spinner("Loading overlay..."):
                cleanup_old_files()
                st.session_state.overlay_path = save_uploaded_file(overlay_file)
                st.session_state.overlay_is_image = False
                
                try:
                    # Validate video file
                    is_valid, duration, width, height = validate_video_file(st.session_state.overlay_path)
                    
                    if not is_valid:
                        st.error("Invalid video file. Please upload a valid MP4 file.")
                        st.stop()
                    
                    # Load the video
                    st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    
                    st.success(f"✅ Overlay: {overlay_file.name}")
                    st.info(f"Duration: {st.session_state.overlay_duration:.1f}s")
                    st.caption(f"Resolution: {width}×{height}")
                    
                    # Show preview
                    with st.spinner("Generating preview..."):
                        preview_img = show_single_frame_preview(st.session_state.overlay_path)
                        if preview_img:
                            st.image(preview_img, caption="Overlay preview", use_column_width=True)
                        else:
                            st.warning("Could not generate preview")
                    
                    st.session_state.overlay_loaded = True
                    
                except Exception as e:
                    st.error(f"Error loading overlay: {str(e)}")
                    st.info("""
                    **Common solutions:**
                    1. Convert video to MP4 format
                    2. Ensure video has standard codec (H.264)
                    3. Try a shorter video clip
                    """)

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_loaded and st.session_state.bg_duration > 0:
    st.subheader("Trim Settings")
    
    # Audio trim settings
    st.markdown("**Audio Duration**")
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
        audio_duration = st.slider(
            "Audio Duration (seconds)",
            1.0,
            float(max_audio_duration),
            min(30.0, float(max_audio_duration)),
            0.5,
            key="audio_duration"
        )
    
    audio_end = audio_start + audio_duration
    st.info(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s total)")

if st.session_state.overlay_loaded and st.session_state.overlay_duration > 0:
    # Overlay trim settings
    st.markdown("**Overlay Video Trim**")
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
        overlay_duration = st.slider(
            "Overlay Duration (seconds)",
            1.0,
            float(max_overlay_duration),
            min(30.0, float(max_overlay_duration)),
            0.5,
            key="overlay_duration"
        )
    
    overlay_end = overlay_start + overlay_duration
    st.info(f"🎥 Overlay: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")

# ---------- IMPROVED PROCESS FUNCTION ----------
def process_video_no_resize():
    """Combine audio and video without any resizing"""
    try:
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 30)
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration', 30)
        overlay_end = overlay_start + overlay_duration_val
        
        # Extract audio
        with st.spinner("📻 Extracting audio..."):
            if st.session_state.bg_is_video and st.session_state.bg_clip:
                if st.session_state.bg_clip.audio is not None:
                    audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
                else:
                    st.error("No audio in video file")
                    return None, 0, 0, 0
            else:
                # Load audio file fresh
                try:
                    audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
                except:
                    st.error("Could not load audio file")
                    return None, 0, 0, 0
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video (NO RESIZING)
        with st.spinner("🎬 Processing overlay video..."):
            # Trim overlay
            overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
            
            # Match durations - loop overlay if shorter than audio
            if overlay.duration < final_audio_duration:
                loops_needed = int(final_audio_duration / overlay.duration) + 1
                overlay_loops = [overlay] * loops_needed
                overlay = concatenate_videoclips(overlay_loops, method="compose")
                overlay = overlay.subclip(0, final_audio_duration)
            elif overlay.duration > final_audio_duration:
                overlay = overlay.subclip(0, final_audio_duration)
            
            # Get original dimensions
            width, height = overlay.size
            
            # Add the audio to video
            final_video = overlay.set_audio(audio_clip)
        
        # Save video with proper encoding
        with st.spinner("💾 Saving video..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Write video with optimized settings for mobile compatibility
            final_video.write_videofile(
                output_path,
                fps=overlay.fps,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="192k",
                bitrate="5000k",  # Lower bitrate for better compatibility
                preset='fast',  # Faster encoding
                threads=4,
                remove_temp=True,
                logger=None,
                ffmpeg_params=[
                    '-movflags', '+faststart',  # Enable streaming
                    '-pix_fmt', 'yuv420p',  # Better mobile compatibility
                    '-profile:v', 'baseline',  # Maximum compatibility
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
        st.error("Try converting your videos to MP4 format with H.264 codec")
        with st.expander("Error details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0

# ---------- CREATE BUTTON ----------
st.divider()

# Check if both files are uploaded and loaded
files_ready = (st.session_state.bg_loaded and st.session_state.overlay_loaded and 
               st.session_state.bg_path and st.session_state.overlay_path)

create_disabled = not files_ready

if st.button("🎬 Create Final Video", 
             type="primary", 
             disabled=create_disabled,
             use_container_width=True):
    
    if not files_ready:
        st.warning("⚠️ Please upload both background and overlay files first")
        st.stop()
    
    # Process video
    with st.spinner("🚀 Creating your video..."):
        output_path, duration, width, height = process_video_no_resize()
    
    if output_path and os.path.exists(output_path):
        st.success("✅ Video created successfully!")
        
        # Show video with better container
        st.subheader("🎥 Your Video Preview")
        
        # Create a container for the video
        video_container = st.container()
        
        with video_container:
            try:
                # Read video file as bytes for display
                with open(output_path, "rb") as video_file:
                    video_bytes = video_file.read()
                
                # Display video
                st.video(video_bytes, format="video/mp4")
                
            except Exception as e:
                st.warning("Preview unavailable. Please download the video to view it.")
                st.info("This is usually a browser compatibility issue. The video file is created successfully.")
        
        # Show video info
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
            video_data = f.read()
            
            st.download_button(
                "📥 Download Video",
                video_data,
                file_name=f"mobile_video_{width}x{height}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Show conversion tips if needed
        if file_size > 50:  # If file is larger than 50MB
            st.info("💡 **Tip**: For smaller file size, try using shorter clips or lower the audio bitrate in the code.")
        
        # Cleanup
        cleanup_old_files()
        gc.collect()
        
    else:
        st.error("❌ Failed to create video. Please try again with different files.")

# ---------- TROUBLESHOOTING SECTION ----------
with st.expander("🔧 Troubleshooting Common Issues"):
    st.markdown("""
    ### If videos don't show overlay or have issues:
    
    **1. Convert to MP4/H.264:**
    - Use HandBrake or FFmpeg to convert videos
    - Command: `ffmpeg -i input.mov -c:v libx264 -c:a aac output.mp4`
    
    **2. Check video codec:**
    - Ensure videos use H.264 codec
    - Audio should be AAC
    
    **3. Reduce video resolution:**
    - Try 1080p or 720p instead of 4K
    - Large files may cause processing issues
    
    **4. Clear cache:**
    - Streamlit caches files, sometimes causing issues
    - Use "Clear cache" in Streamlit menu
    
    **5. Shorter clips:**
    - Try with shorter videos (under 2 minutes) first
    - Then gradually increase duration
    """)

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Mobile Video Maker
    
    **Features:**
    - Trim audio from any video/audio file
    - Trim overlay video
    - Combine without resizing (keeps original quality)
    - Mobile-optimized output
    
    **Steps:**
    1. **Upload Background** - MP3, MP4, or MOV with audio
    2. **Upload Overlay** - MP4 video (best compatibility)
    3. **Trim Audio** - Select start point and duration
    4. **Trim Video** - Select start point and duration
    5. **Click Create** - Get your combined video
    
    **For best results:**
    - Use MP4 files with H.264 codec
    - Keep videos under 5 minutes for faster processing
    - Ensure overlay video has standard resolution (720p, 1080p)
    
    **Output:** Video with original dimensions, ready for mobile
    """)

# ---------- FOOTER ----------
st.divider()
st.caption(f"{my_title} • No resizing • Mobile compatible • Keep original dimensions")
