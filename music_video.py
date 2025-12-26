"""
Video Maker V 3.0 - Enhanced Video Editor
This application allows users to combine audio from one file with video from another,
with independent trimming controls for both media types.
Features: Separate start/end sliders, dynamic title, no resizing.
"""

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
# Configure the page layout and settings
st.set_page_config(
    page_title="Video Maker V 3.0",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide the sidebar and style buttons for mobile
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    /* Mobile-friendly buttons */
    .stButton > button {
        width: 100%;
    }
    /* Style for the dynamic title */
    .dynamic-title {
        background: linear-gradient(45deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ---------- DYNAMIC TITLE FUNCTION ----------
def generate_dynamic_title():
    """
    Generate a dynamic title based on current session state variables.
    This title updates automatically when trim values change.
    """
    # Base title components
    title_parts = ["🎬 Video Maker V 3.0"]
    
    # Add audio duration info if available
    if st.session_state.get('bg_duration', 0) > 0:
        audio_start = st.session_state.get('audio_start', 0)
        audio_end = st.session_state.get('audio_end', 0)
        audio_duration = audio_end - audio_start
        
        if audio_duration > 0:
            title_parts.append(f"🎵 {audio_duration:.1f}s")
    
    # Add video duration info if available
    if st.session_state.get('overlay_duration', 0) > 0:
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_end = st.session_state.get('overlay_end', 0)
        overlay_duration = overlay_end - overlay_start
        
        if overlay_duration > 0:
            title_parts.append(f"📹 {overlay_duration:.1f}s")
    
    # Combine all parts
    full_title = " • ".join(title_parts)
    return full_title

# ---------- SESSION STATE INITIALIZATION ----------
# Define default values for session state variables
session_defaults = {
    # Background media variables
    'bg_clip': None,                    # MoviePy clip object for background
    'overlay_clip': None,               # MoviePy clip object for overlay
    'bg_duration': 0,                   # Total duration of background media (seconds)
    'overlay_duration': 0,              # Total duration of overlay media (seconds)
    'bg_path': None,                    # Temporary file path for background
    'overlay_path': None,               # Temporary file path for overlay
    'bg_is_video': False,               # Boolean: is background a video file?
    'overlay_is_image': False,          # Boolean: is overlay an image file? (not used)
    'prev_bg_file': None,               # Previous background filename for change detection
    'prev_overlay_file': None,          # Previous overlay filename for change detection
    
    # Trim variables for audio/background
    'audio_start': 0.0,                 # Start time for audio trim (seconds)
    'audio_end': 0.0,                   # End time for audio trim (seconds)
    
    # Trim variables for overlay video
    'overlay_start': 0.0,               # Start time for video trim (seconds)
    'overlay_end': 0.0,                 # End time for video trim (seconds)
    
    # UI state variables
    'last_title': "",                   # Store last generated title for change detection
    'title_changed': False              # Flag to indicate title needs updating
}

# Initialize session state with default values
for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- FILE MANAGEMENT FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """
    Save uploaded file to a temporary location.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        str: Path to the temporary file
    """
    # Get file extension for proper naming
    file_extension = os.path.splitext(uploaded_file.name)[1]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def show_single_frame_preview(video_path, time_point=1):
    """
    Extract and display a single frame from a video file as a preview.
    
    Args:
        video_path: Path to the video file
        time_point: Time in seconds to extract frame from
        
    Returns:
        PIL.Image: Thumbnail image or None if extraction fails
    """
    try:
        # Load video without audio for faster processing
        clip = VideoFileClip(video_path, audio=False)
        
        # Ensure time_point is within video duration
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        # Extract frame and convert to PIL Image
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Create thumbnail for display
        img.thumbnail((300, 300))
        
        # Clean up resources
        clip.close()
        return img
    except Exception as e:
        st.warning(f"Could not generate preview: {str(e)}")
        return None

# ---------- APP TITLE ----------
# Display dynamic title that updates based on current settings
current_title = generate_dynamic_title()
st.markdown(f"<h1 class='dynamic-title'>{current_title}</h1>", unsafe_allow_html=True)
st.session_state.last_title = current_title  # Store for change detection

st.caption("Trim audio and overlay videos - No resizing - Separate Start/End Controls")

# ---------- FILE UPLOAD SECTION ----------
st.subheader("📁 Upload Files")

# Create two columns for parallel file uploads
col1, col2 = st.columns(2)

with col1:
    # Background file uploader (audio or video)
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a"],
        help="Audio will be extracted from this file. Supports MP3, MP4, MOV, M4A formats."
    )
    
    if background_file:
        # Detect if file has changed since last upload
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None  # Clear old clip
            st.session_state.prev_bg_file = background_file.name  # Update filename
        
        # Process and load the background file
        with st.spinner("Loading background media..."):
            # Save to temporary file
            st.session_state.bg_path = save_uploaded_file(background_file)
            
            # Determine file type by extension
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
            
            try:
                if st.session_state.bg_is_video:
                    # Load as video file and extract audio
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        # Initialize trim points to full duration
                        st.session_state.audio_end = st.session_state.bg_duration
                        st.success(f"✅ Video loaded: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                    else:
                        st.error("No audio track found in video file")
                        st.stop()
                else:
                    # Load as audio-only file
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    # Initialize trim points to full duration
                    st.session_state.audio_end = st.session_state.bg_duration
                    st.success(f"✅ Audio loaded: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                
                # Set title changed flag
                st.session_state.title_changed = True
                    
            except Exception as e:
                st.error(f"Error loading background file: {str(e)}")
                # Clean up on error
                if os.path.exists(st.session_state.bg_path):
                    os.unlink(st.session_state.bg_path)

with col2:
    # Overlay video file uploader
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov"],
        help="Video overlay file. Will not be resized. Supports MP4, MOV formats."
    )
    
    if overlay_file:
        # Detect if file has changed since last upload
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None  # Clear old clip
            st.session_state.prev_overlay_file = overlay_file.name  # Update filename
        
        # Process and load the overlay file
        with st.spinner("Loading overlay video..."):
            # Save to temporary file
            st.session_state.overlay_path = save_uploaded_file(overlay_file)
            
            try:
                # Load video file without audio
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                # Initialize trim points to full duration
                st.session_state.overlay_end = st.session_state.overlay_duration
                st.success(f"✅ Overlay loaded: {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
                
                # Display preview thumbnail
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Overlay preview", use_column_width=True)
                
                # Set title changed flag
                st.session_state.title_changed = True
                    
            except Exception as e:
                st.error(f"Error loading overlay file: {str(e)}")
                # Clean up on error
                if os.path.exists(st.session_state.overlay_path):
                    os.unlink(st.session_state.overlay_path)

# ---------- AUDIO TRIM CONTROLS ----------
if st.session_state.bg_duration > 0:
    st.subheader("🎵 Audio Trim Settings")
    
    # Create two columns for start/end sliders
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Audio Start**")
        # Start time slider for audio
        audio_start = st.slider(
            "Start (seconds)",
            0.0,  # Minimum value
            float(st.session_state.bg_duration),  # Maximum value (full duration)
            float(min(st.session_state.audio_start, st.session_state.bg_duration - 0.1)),  # Current value
            0.1,  # Step size
            key="audio_start_slider",  # Unique key for widget
            label_visibility="collapsed",  # Hide default label
            on_change=lambda: setattr(st.session_state, 'title_changed', True)  # Update title on change
        )
        st.session_state.audio_start = audio_start  # Store in session state
        st.caption(f"Start: {audio_start:.1f}s")  # Display current value
    
    with col2:
        st.markdown("**Audio End**")
        # Calculate minimum end value (start + 0.1 seconds)
        min_end = min(audio_start + 0.1, st.session_state.bg_duration)
        
        # End time slider for audio
        audio_end = st.slider(
            "End (seconds)",
            float(min_end),  # Minimum value (prevents end < start)
            float(st.session_state.bg_duration),  # Maximum value
            float(min(st.session_state.audio_end, st.session_state.bg_duration)),  # Current value
            0.1,  # Step size
            key="audio_end_slider",  # Unique key for widget
            label_visibility="collapsed",  # Hide default label
            on_change=lambda: setattr(st.session_state, 'title_changed', True)  # Update title on change
        )
        st.session_state.audio_end = audio_end  # Store in session state
        st.caption(f"End: {audio_end:.1f}s")  # Display current value
    
    # Calculate and display audio selection info
    audio_duration = audio_end - audio_start
    if audio_duration > 0:
        st.info(f"🎵 Audio selection: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)")
        # Update title if duration changed
        if st.session_state.title_changed:
            new_title = generate_dynamic_title()
            if new_title != st.session_state.last_title:
                st.session_state.last_title = new_title
                st.rerun()  # Force UI refresh to update title
    else:
        st.error("Audio selection must be at least 0.1 seconds")

# ---------- VIDEO TRIM CONTROLS ----------
if st.session_state.overlay_duration > 0:
    st.subheader("🎬 Overlay Video Trim Settings")
    
    # Create two columns for start/end sliders
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Video Start**")
        # Start time slider for video
        overlay_start = st.slider(
            "Start (seconds)",
            0.0,  # Minimum value
            float(st.session_state.overlay_duration),  # Maximum value
            float(min(st.session_state.overlay_start, st.session_state.overlay_duration - 0.1)),  # Current value
            0.1,  # Step size
            key="overlay_start_slider",  # Unique key for widget
            label_visibility="collapsed",  # Hide default label
            on_change=lambda: setattr(st.session_state, 'title_changed', True)  # Update title on change
        )
        st.session_state.overlay_start = overlay_start  # Store in session state
        st.caption(f"Start: {overlay_start:.1f}s")  # Display current value
    
    with col2:
        st.markdown("**Video End**")
        # Calculate minimum end value (start + 0.1 seconds)
        min_end = min(overlay_start + 0.1, st.session_state.overlay_duration)
        
        # End time slider for video
        overlay_end = st.slider(
            "End (seconds)",
            float(min_end),  # Minimum value (prevents end < start)
            float(st.session_state.overlay_duration),  # Maximum value
            float(min(st.session_state.overlay_end, st.session_state.overlay_duration)),  # Current value
            0.1,  # Step size
            key="overlay_end_slider",  # Unique key for widget
            label_visibility="collapsed",  # Hide default label
            on_change=lambda: setattr(st.session_state, 'title_changed', True)  # Update title on change
        )
        st.session_state.overlay_end = overlay_end  # Store in session state
        st.caption(f"End: {overlay_end:.1f}s")  # Display current value
    
    # Calculate and display video selection info
    overlay_duration = overlay_end - overlay_start
    if overlay_duration > 0:
        st.info(f"🎬 Video selection: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s)")
        # Update title if duration changed
        if st.session_state.title_changed:
            new_title = generate_dynamic_title()
            if new_title != st.session_state.last_title:
                st.session_state.last_title = new_title
                st.rerun()  # Force UI refresh to update title
    else:
        st.error("Video selection must be at least 0.1 seconds")

# Reset title changed flag after updates
if st.session_state.title_changed:
    st.session_state.title_changed = False

# ---------- VIDEO PROCESSING FUNCTION ----------
def process_video_no_resize():
    """
    Combine trimmed audio with trimmed video without resizing.
    
    Steps:
    1. Extract audio segment based on start/end times
    2. Extract video segment based on start/end times
    3. Loop video if shorter than audio
    4. Combine audio and video
    5. Save to temporary file
    
    Returns:
        tuple: (output_path, duration, width, height) or (None, 0, 0, 0) on error
    """
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
        
        # Calculate final audio duration
        final_audio_duration = audio_end - audio_start
        
        # Step 1: Extract audio segment
        with st.spinner("Extracting audio segment..."):
            if st.session_state.bg_is_video:
                # Extract audio from video file
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                # Load audio from audio-only file
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        # Step 2: Process video segment
        with st.spinner("Processing video segment..."):
            # Extract video segment
            overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
            
            # Step 3: Match durations
            # If video is shorter than audio, loop it
            if overlay.duration < final_audio_duration:
                loops_needed = int(final_audio_duration / overlay.duration) + 1
                overlay_loops = [overlay] * loops_needed
                overlay = concatenate_videoclips(overlay_loops)
                overlay = overlay.subclip(0, final_audio_duration)
            # If video is longer than audio, trim it
            elif overlay.duration > final_audio_duration:
                overlay = overlay.subclip(0, final_audio_duration)
            
            # Step 4: Combine audio and video (NO RESIZING - keep original dimensions)
            final_video = overlay.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
        
        # Step 5: Save video
        with st.spinner("Encoding final video..."):
            # Create temporary output file
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Get original video dimensions
            width, height = overlay.size
            
            # Write video with high-quality settings
            final_video.write_videofile(
                output_path,
                fps=overlay.fps if hasattr(overlay, 'fps') else 30,  # Use original FPS
                codec="libx264",  # Standard video codec
                audio_codec="aac",  # Standard audio codec
                bitrate="8M",  # Good quality bitrate
                verbose=False,  # Suppress verbose output
                logger=None,  # Suppress logger
                preset='medium',  # Encoding speed/quality balance
                ffmpeg_params=['-movflags', '+faststart']  # Web optimization
            )
        
        # Step 6: Clean up resources
        audio_clip.close()
        overlay.close()
        final_video.close()
        
        return output_path, final_audio_duration, width, height
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        # Provide detailed error info in expandable section
        import traceback
        with st.expander("🔍 Error details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0

# ---------- CREATE VIDEO BUTTON ----------
st.divider()

# Check if both files are uploaded
files_ready = st.session_state.bg_path and st.session_state.overlay_path

# Validate slider values before enabling create button
sliders_valid = True
if files_ready:
    if st.session_state.audio_end <= st.session_state.audio_start:
        st.warning("⚠️ Audio end must be greater than audio start")
        sliders_valid = False
    if st.session_state.overlay_end <= st.session_state.overlay_start:
        st.warning("⚠️ Overlay end must be greater than overlay start")
        sliders_valid = False

# Create video button (primary action)
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
    
    # Display results if successful
    if output_path and os.path.exists(output_path):
        st.success("✅ Video created successfully!")
        
        # Display video preview
        st.subheader("Your Video")
        try:
            st.video(output_path)
        except:
            st.info("Video preview (download to view)")
        
        # Display video metadata
        file_size = os.path.getsize(output_path) / (1024 * 1024)  # Convert to MB
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("File Size", f"{file_size:.1f}MB")
        
        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "📥 Download Video",
                f,
                file_name=f"video_{width}x{height}_{duration:.0f}s.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Clean up temporary input files
        try:
            if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
                os.unlink(st.session_state.bg_path)
            if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
                os.unlink(st.session_state.overlay_path)
        except Exception as e:
            st.warning(f"Could not clean up temporary files: {str(e)}")
        
        # Clear session state for next operation
        for key in ['bg_path', 'overlay_path', 'bg_clip', 'overlay_clip']:
            if key in st.session_state:
                st.session_state[key] = None
        
        # Force garbage collection
        gc.collect()

# ---------- INSTRUCTIONS SECTION ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Video Maker V 3.0 - Complete Guide
    
    **✨ Key Features:**
    1. **Separate Start/End Controls** - Independent sliders for precise trimming
    2. **Dynamic Title** - Title updates automatically with your selections
    3. **No Resizing** - Original video dimensions are preserved
    4. **Audio Extraction** - Extract audio from video files or use audio files
    5. **Auto-looping** - Short videos automatically loop to match audio length
    
    **📋 Step-by-Step Instructions:**
    
    1. **Upload Files**
       - **Background**: Upload any audio or video file (MP3, MP4, MOV, M4A)
       - **Overlay**: Upload a video file (MP4, MOV) - this provides the visuals
    
    2. **Set Trim Points**
       - **Audio**: Use the start and end sliders to select the exact audio segment
       - **Video**: Use the start and end sliders to select the exact video segment
       - **Note**: The title updates automatically showing selected durations
    
    3. **Create Video**
       - Click "Create Final Video" to combine your selections
       - The app will match video duration to audio (looping if needed)
       - No resizing - your video keeps its original quality and dimensions
    
    4. **Download Result**
       - Preview your video directly in the browser
       - Download the final MP4 file with one click
    
    **⚙️ Technical Details:**
    - **Codec**: H.264 video with AAC audio (compatible with all devices)
    - **Quality**: 8 Mbps bitrate for good quality/size balance
    - **Processing**: FFmpeg-based with fast encoding preset
    - **Compatibility**: Output is web-optimized with fast-start flag
    
    **💡 Pro Tips:**
    - For best results, use videos with matching aspect ratios
    - Longer audio segments with shorter videos create seamless loops
    - The app automatically prevents invalid start/end combinations
    - All processing happens locally - your files are not uploaded to any server
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Video Maker V 3.0 • No Resizing • Start/End Controls • Dynamic Title • Local Processing")
