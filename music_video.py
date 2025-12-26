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

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Video Maker V 2:1",
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
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title("🎬 Video Maker V 2:1")
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
    'audio_start': 0.0,
    'audio_end': 0.0,
    'overlay_start': 0.0,
    'overlay_end': 0.0
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
                        # Initialize end to full duration
                        st.session_state.audio_end = st.session_state.bg_duration
                        st.success(f"✅ Video: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                    else:
                        st.error("No audio in video")
                        st.stop()
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    # Initialize end to full duration
                    st.session_state.audio_end = st.session_state.bg_duration
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
                # Initialize end to full duration
                st.session_state.overlay_end = st.session_state.overlay_duration
                st.success(f"✅ Overlay: {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Overlay preview", use_column_width=True)
                    
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- SEPARATE START AND END SLIDERS ----------
if st.session_state.bg_duration > 0:
    st.subheader("Audio Trim Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Audio Start**")
        # Start slider
        audio_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            float(min(st.session_state.audio_start, st.session_state.bg_duration - 0.1)),
            0.1,
            key="audio_start_slider",
            label_visibility="collapsed"
        )
        st.session_state.audio_start = audio_start
        st.caption(f"Start: {audio_start:.1f}s")
    
    with col2:
        st.markdown("**Audio End**")
        # End slider - minimum is start + 0.1 seconds
        min_end = min(audio_start + 0.1, st.session_state.bg_duration)
        audio_end = st.slider(
            "End (seconds)",
            float(min_end),
            float(st.session_state.bg_duration),
            float(min(st.session_state.audio_end, st.session_state.bg_duration)),
            0.1,
            key="audio_end_slider",
            label_visibility="collapsed"
        )
        st.session_state.audio_end = audio_end
        st.caption(f"End: {audio_end:.1f}s")
    
    # Show duration info
    audio_duration = audio_end - audio_start
    if audio_duration > 0:
        st.info(f"🎵 Audio selection: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)")
    else:
        st.error("Audio selection must be at least 0.1 seconds")

if st.session_state.overlay_duration > 0:
    st.subheader("Overlay Video Trim Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Overlay Start**")
        # Start slider
        overlay_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.overlay_duration),
            float(min(st.session_state.overlay_start, st.session_state.overlay_duration - 0.1)),
            0.1,
            key="overlay_start_slider",
            label_visibility="collapsed"
        )
        st.session_state.overlay_start = overlay_start
        st.caption(f"Start: {overlay_start:.1f}s")
    
    with col2:
        st.markdown("**Overlay End**")
        # End slider - minimum is start + 0.1 seconds
        min_end = min(overlay_start + 0.1, st.session_state.overlay_duration)
        overlay_end = st.slider(
            "End (seconds)",
            float(min_end),
            float(st.session_state.overlay_duration),
            float(min(st.session_state.overlay_end, st.session_state.overlay_duration)),
            0.1,
            key="overlay_end_slider",
            label_visibility="collapsed"
        )
        st.session_state.overlay_end = overlay_end
        st.caption(f"End: {overlay_end:.1f}s")
    
    # Show duration info
    overlay_duration = overlay_end - overlay_start
    if overlay_duration > 0:
        st.info(f"🎬 Overlay selection: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s)")
    else:
        st.error("Overlay selection must be at least 0.1 seconds")

# ---------- PROCESS FUNCTION (NO RESIZING) ----------
def process_video_no_resize():
    """Combine audio and video without any resizing"""
    try:
        # Get trim values from session state
        audio_start = st.session_state.get('audio_start', 0)
        audio_end = st.session_state.get('audio_end', 0)
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_end = st.session_state.get('overlay_end', 0)
        
        # Validate durations
        if audio_end <= audio_start:
            st.error("Audio end must be greater than audio start")
            return None, 0, 0, 0
        
        if overlay_end <= overlay_start:
            st.error("Overlay end must be greater than overlay start")
            return None, 0, 0, 0
        
        final_audio_duration = audio_end - audio_start
        
        # Extract audio
        with st.spinner("Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                # Load audio file fresh
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
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

# Validate slider values
sliders_valid = True
if files_ready:
    if st.session_state.audio_end <= st.session_state.audio_start:
        st.warning("⚠️ Audio end must be greater than audio start")
        sliders_valid = False
    if st.session_state.overlay_end <= st.session_state.overlay_start:
        st.warning("⚠️ Overlay end must be greater than overlay start")
        sliders_valid = False

if st.button("🎬 Create Final Video", 
             type="primary", 
             disabled=not files_ready or not sliders_valid,
             use_container_width=True):
    
    if not files_ready:
        st.warning("Please upload both background and overlay files first")
        st.stop()
    
    if not sliders_valid:
        st.warning("Please fix the slider values first")
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
    ### Simple Video Trimmer with Start & End Controls
    
    **What this does:**
    1. Takes audio from your background file (MP3/MP4)
    2. Takes video from your overlay file (MP4/MOV)
    3. Trims both using separate start and end sliders
    4. Combines them WITHOUT resizing
    5. Outputs the video with original dimensions
    
    **Steps:**
    1. **Upload Background** - Any audio or video file
    2. **Upload Overlay** - Video file (will not be resized)
    3. **Trim Audio** - Use separate sliders for start and end points
    4. **Trim Video** - Use separate sliders for start and end points
    5. **Click Create** - Get your combined video
    
    **Features:**
    - Independent start/end controls for each media
    - Live duration calculation
    - Validation to ensure end > start
    - Original video dimensions preserved
    
    **Note:** Videos keep their original size - no resizing or black borders.
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Video Trimmer • No resizing • Keep original dimensions • Start/End Controls")
