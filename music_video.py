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
my_title = "🎬 Mobile Video Maker V 23" #update version with any change by adding 1
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
st.caption("Combine audio with video or image overlays - No resizing | Single slider for easy trimming")

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
    'overlay_image': None,
    'prev_bg_file': None,
    'prev_overlay_file': None,
    'audio_trim_values': [0.0, 30.0],  # Default: start=0, end=30
    'overlay_trim_values': [0.0, 30.0],  # Default: start=0, end=30
    'image_duration': 5.0  # Default duration for images
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
        "Overlay (Video or Image)",
        type=["mp4", "mov", "jpg", "jpeg", "png", "gif"],
        help="Video overlay or static image (will not be resized)"
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.overlay_image = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save and load
        with st.spinner("Loading overlay..."):
            st.session_state.overlay_path = save_uploaded_file(overlay_file)
            file_ext = os.path.splitext(overlay_file.name)[1].lower()
            st.session_state.overlay_is_image = file_ext in ['.jpg', '.jpeg', '.png', '.gif']
            
            try:
                if st.session_state.overlay_is_image:
                    # Load image
                    st.session_state.overlay_image = Image.open(st.session_state.overlay_path)
                    st.session_state.overlay_duration = 0  # Images don't have duration
                    st.success(f"✅ Image: {overlay_file.name}")
                    
                    # Show preview
                    img_preview = st.session_state.overlay_image.copy()
                    img_preview.thumbnail((300, 300))
                    st.image(img_preview, caption="Image preview", use_column_width=True)
                    
                    # Set default image duration
                    if st.session_state.bg_duration > 0:
                        st.session_state.image_duration = min(30.0, st.session_state.bg_duration)
                    
                else:
                    # Load video
                    st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    # Reset trim values to full duration (max 30 seconds or actual duration)
                    max_end = min(30.0, st.session_state.overlay_duration)
                    st.session_state.overlay_trim_values = [0.0, max_end]
                    st.success(f"✅ Video: {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
                    
                    # Show preview
                    preview_img = show_single_frame_preview(st.session_state.overlay_path)
                    if preview_img:
                        st.image(preview_img, caption="Video preview", use_column_width=True)
                        
            except Exception as e:
                st.error(f"Error: {str(e)}")

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("Audio Settings")
    
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

# ---------- OVERLAY SETTINGS (ONLY FOR VIDEO) ----------
if st.session_state.overlay_duration > 0 and not st.session_state.overlay_is_image:
    # Single range slider for video overlay trim
    st.subheader("Video Overlay Settings")
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

# ---------- IMAGE OVERLAY SETTINGS ----------
elif st.session_state.overlay_is_image and st.session_state.bg_duration > 0:
    st.subheader("Image Overlay Settings")
    
    # For images, only show duration setting
    st.markdown("**Image Display Duration**")
    st.caption("How long the image should appear in the video")
    
    # Set max duration based on audio selection
    audio_start, audio_end = st.session_state.audio_trim_values
    max_image_duration = audio_end - audio_start
    
    # Image duration slider
    image_duration = st.slider(
        "Image duration (seconds)",
        min_value=1.0,
        max_value=float(max_image_duration),
        value=min(30.0, float(max_image_duration)),
        step=0.5,
        format="%.1f s",
        key="image_duration_slider",
        help=f"How long to display the image (max: {max_image_duration:.1f}s)"
    )
    
    st.session_state.image_duration = image_duration
    
    st.info(f"Image will be displayed for {format_time(image_duration)} alongside the audio.")

# ---------- PROCESS FUNCTION (WITH IMAGE SUPPORT) ----------
def process_video_with_image():
    """Combine audio with video or image overlay without any resizing"""
    try:
        # Get audio trim values
        audio_start, audio_end = st.session_state.get('audio_trim_values', [0.0, 30.0])
        
        # Extract audio
        with st.spinner("Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                # Load audio file fresh
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay (Video or Image)
        with st.spinner("Processing overlay..."):
            if st.session_state.overlay_is_image:
                # ----- PROCESS IMAGE OVERLAY -----
                # Create video clip from image
                img_array = np.array(st.session_state.overlay_image)
                
                # Use image duration from slider
                image_duration = st.session_state.image_duration
                
                # Ensure image doesn't exceed audio duration
                if image_duration > final_audio_duration:
                    image_duration = final_audio_duration
                
                # Create image clip
                overlay = ImageClip(img_array, duration=image_duration)
                
                # If image is shorter than audio, create black background for remaining time
                if image_duration < final_audio_duration:
                    # Create black background for the full duration
                    from moviepy.video.VideoClip import ColorClip
                    bg_clip = ColorClip(size=overlay.size, color=(0, 0, 0), duration=final_audio_duration)
                    
                    # Composite image on top of black background
                    overlay = overlay.set_position(('center', 'center'))
                    final_video = CompositeVideoClip([bg_clip, overlay], duration=final_audio_duration)
                else:
                    final_video = overlay
                
            else:
                # ----- PROCESS VIDEO OVERLAY -----
                # Get video trim values
                overlay_start, overlay_end = st.session_state.get('overlay_trim_values', [0.0, 30.0])
                
                # Trim overlay video
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
                final_video = overlay
            
            # Add audio to final video
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
        
        # Save video
        with st.spinner("Saving video..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Get original dimensions
            width, height = final_video.size
            
            # Set appropriate fps
            fps = 30
            if not st.session_state.overlay_is_image:
                fps = overlay.fps if hasattr(overlay, 'fps') else 30
            
            final_video.write_videofile(
                output_path,
                fps=fps,
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
        if hasattr(overlay, 'close'):
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
    output_path, duration, width, height = process_video_with_image()
    
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
        
        overlay_type = "Image" if st.session_state.overlay_is_image else "Video"
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Size", f"{file_size:.1f}MB")
        
        # Display overlay type
        st.info(f"Overlay type: {overlay_type}")
        
        # Download button
        with open(output_path, "rb") as f:
            file_label = "image" if st.session_state.overlay_is_image else "video"
            st.download_button(
                f"📥 Download {overlay_type} Video",
                f,
                file_name=f"combined_{file_label}_overlay_{width}x{height}.mp4",
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
        for key in ['bg_path', 'overlay_path', 'bg_clip', 'overlay_clip', 'overlay_image']:
            if key in st.session_state:
                st.session_state[key] = None
        
        gc.collect()

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Audio + Video/Image Combiner
    
    **What this does:**
    1. Takes audio from your background file (MP3/MP4)
    2. Takes video OR image from your overlay file
    3. Trims audio using single slider
    4. For videos: Trims video using single slider
    5. For images: Sets display duration
    6. Combines them WITHOUT resizing
    7. Outputs the video with original dimensions
    
    **Steps:**
    1. **Upload Background** - Any audio or video file with audio
    2. **Upload Overlay** - Video (MP4/MOV) or Image (JPG/PNG/GIF)
    3. **Trim Audio** - Use the single slider to select start AND end time
    4. **If Video Overlay:** Trim video with the single slider
    5. **If Image Overlay:** Set how long to display the image
    6. **Click Create** - Get your combined video
    
    **Features:**
    - **Video Overlay:** Can be trimmed with range slider
    - **Image Overlay:** Static image displayed for selected duration
    - **No Resizing:** Original dimensions preserved
    - **Mobile Friendly:** Single sliders for easy trimming
    
    **Note:** 
    - Videos keep their original size - no resizing or black borders
    - Images are centered on black background
    - Image duration cannot exceed selected audio duration
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Video/Image Combiner • No resizing • Single slider trimming • Keep original dimensions")
