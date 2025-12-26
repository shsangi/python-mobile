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
    concatenate_videoclips
)
my_title = "🎬 Mobile Video Maker V 22" #update version with any change by adding 1
# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title= my_title,
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide the sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Mobile-friendly buttons */
    .stButton > button {
        width: 100%;
    }
    /* Custom range slider style */
    .stSlider > div > div > div {
        height: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - No resizing | Single slider for easy trimming")

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
    'audio_trim_values': [0.0, 30.0],  # Default: start=0, end=30
    'overlay_trim_values': [0.0, 30.0]  # Default: start=0, end=30
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- SIMPLIFIED HELPER FUNCTIONS ----------
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
        img.thumbnail((300, 300))
        
        clip.close()
        return img
    except:
        return None

def format_time(seconds):
    """Format seconds to MM:SS or HH:MM:SS if needed"""
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

# ---------- UPLOAD SECTIONS ----------
st.subheader("Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a"],
        help="Audio will be extracted from this file"
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save and load
        with st.spinner("Loading background..."):
            st.session_state.bg_path = save_uploaded_file(background_file)
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
            
            try:
                if st.session_state.bg_is_video:
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        # Reset trim values to full duration (max 30 seconds or actual duration)
                        max_end = min(30.0, st.session_state.bg_duration)
                        st.session_state.audio_trim_values = [0.0, max_end]
                        st.success(f"✅ Video: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                    else:
                        st.error("No audio in video")
                        st.stop()
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    # Reset trim values to full duration (max 30 seconds or actual duration)
                    max_end = min(30.0, st.session_state.bg_duration)
                    st.session_state.audio_trim_values = [0.0, max_end]
                    st.success(f"✅ Audio: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                
            except Exception as e:
                st.error(f"Error: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov"],
        help="Video overlay (will not be resized)"
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
                # Reset trim values to full duration (max 30 seconds or actual duration)
                max_end = min(30.0, st.session_state.overlay_duration)
                st.session_state.overlay_trim_values = [0.0, max_end]
                st.success(f"✅ Overlay: {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Overlay preview", use_column_width=True)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- SINGLE RANGE SLIDERS FOR TRIM ----------
if st.session_state.bg_duration > 0:
    st.subheader("Trim Settings")
    
    # Single range slider for audio trim
    st.markdown("**Audio Selection**")
    st.caption("Drag the handles to select start and end time")
    
    # Get max duration for slider
    max_duration = float(st.session_state.bg_duration)
    
    # Create range slider
    audio_trim_values = st.slider(
        "Select audio start and end time",
        min_value=0.0,
        max_value=max_duration,
        value=st.session_state.audio_trim_values,
        step=0.5,
        format="%.1f s",
        key="audio_range_slider",
        help=f"Drag the left handle for start time, right handle for end time. Max duration: {max_duration:.1f}s"
    )
    
    # Store in session state
    st.session_state.audio_trim_values = audio_trim_values
    
    # Calculate duration
    audio_start, audio_end = audio_trim_values
    audio_duration = audio_end - audio_start
    
    # Display formatted times
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Start", f"{format_time(audio_start)}")
    with col2:
        st.metric("End", f"{format_time(audio_end)}")
    with col3:
        st.metric("Duration", f"{format_time(audio_duration)}")
    
    # Visual timeline
    st.progress(audio_end / max_duration, text=f"Selected: {audio_duration:.1f}s of {max_duration:.1f}s total")

if st.session_state.overlay_duration > 0:
    # Single range slider for overlay trim
    st.markdown("**Overlay Video Selection**")
    st.caption("Drag the handles to select start and end time for video")
    
    # Get max duration for slider
    max_overlay_duration = float(st.session_state.overlay_duration)
    
    # Create range slider
    overlay_trim_values = st.slider(
        "Select overlay video start and end time",
        min_value=0.0,
        max_value=max_overlay_duration,
        value=st.session_state.overlay_trim_values,
        step=0.5,
        format="%.1f s",
        key="overlay_range_slider",
        help=f"Drag the left handle for start time, right handle for end time. Max duration: {max_overlay_duration:.1f}s"
    )
    
    # Store in session state
    st.session_state.overlay_trim_values = overlay_trim_values
    
    # Calculate duration
    overlay_start, overlay_end = overlay_trim_values
    overlay_duration_val = overlay_end - overlay_start
    
    # Display formatted times
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Start", f"{format_time(overlay_start)}")
    with col2:
        st.metric("End", f"{format_time(overlay_end)}")
    with col3:
        st.metric("Duration", f"{format_time(overlay_duration_val)}")
    
    # Visual timeline
    st.progress(overlay_end / max_overlay_duration, text=f"Selected: {overlay_duration_val:.1f}s of {max_overlay_duration:.1f}s total")

# ---------- PROCESS FUNCTION (NO RESIZING) ----------
def process_video_no_resize():
    """Combine audio and video without any resizing"""
    try:
        # Get trim values from range sliders
        audio_start, audio_end = st.session_state.get('audio_trim_values', [0.0, 30.0])
        overlay_start, overlay_end = st.session_state.get('overlay_trim_values', [0.0, 30.0])
        
        # Extract audio
        with st.spinner("Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                # Load audio file fresh
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video (NO RESIZING)
        with st.spinner("Processing overlay..."):
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
            
            # NO RESIZING - keep original dimensions
            # Just add the audio
            final_video = overlay.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
        
        # Save video
        with st.spinner("Saving video..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Get original dimensions
            width, height = overlay.size
            
            final_video.write_videofile(
                output_path,
                fps=overlay.fps if hasattr(overlay, 'fps') else 30,
                codec="libx264",
                audio_codec="aac",
                bitrate="8M",
                verbose=False,
                logger=None,
                preset='medium',
                ffmpeg_params=['-movflags', '+faststart']
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
    
    # Process video
    output_path, duration, width, height = process_video_no_resize()
    
    if output_path and os.path.exists(output_path):
        st.success("✅ Video created successfully!")
        
        # Show video
        st.subheader("Your Video")
        
        try:
            st.video(output_path)
        except:
            st.info("Video preview (download to view)")
        
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
                f,
                file_name=f"trimmed_video_{width}x{height}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Cleanup temp files
        try:
            if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
                os.unlink(st.session_state.bg_path)
            if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
                os.unlink(st.session_state.overlay_path)
        except:
            pass
        
        # Clear session
        for key in ['bg_path', 'overlay_path', 'bg_clip', 'overlay_clip']:
            if key in st.session_state:
                st.session_state[key] = None
        
        gc.collect()

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Simple Video Trimmer
    
    **What this does:**
    1. Takes audio from your background file (MP3/MP4)
    2. Takes video from your overlay file (MP4/MOV)
    3. Trims both using single range sliders (easy to use!)
    4. Combines them WITHOUT resizing
    5. Outputs the video with original dimensions
    
    **Steps:**
    1. **Upload Background** - Any audio or video file
    2. **Upload Overlay** - Video file (will not be resized)
    3. **Trim Audio** - Use the single slider to select start AND end time
    4. **Trim Video** - Use the single slider to select start AND end time
    5. **Click Create** - Get your combined video
    
    **Easy Trimming:**
    - Each slider has TWO handles (left and right)
    - Drag LEFT handle to set start time
    - Drag RIGHT handle to set end time
    - See timeline preview below each slider
    
    **Note:** Videos keep their original size - no resizing or black borders.
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Video Trimmer • No resizing • Single slider trimming • Keep original dimensions")
