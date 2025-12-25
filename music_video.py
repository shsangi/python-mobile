import streamlit as st
import tempfile
import os
import numpy as np
from PIL import Image

import moviepy
import decorator
import imageio_ffmpeg

from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    CompositeVideoClip,
    ColorClip,
    concatenate_videoclips
)

# Add version tracking
VERSION = "2.4.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Mobile Video Maker", layout="centered")
st.title(f"📱 Mobile Video Maker v{VERSION}")
st.markdown("Create mobile videos that fill the entire screen")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
App Version     : {VERSION}
MoviePy        : {moviepy.__version__}
Pillow         : {Image.__version__}
""")

# ---------- UPLOADS ----------
col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Music",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi"],
        help="Upload audio or video file - only audio will be used"
    )

with col2:
    overlay_file = st.file_uploader(
        "Screen Content (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg"],
        help="Upload image or video - will fill the entire screen"
    )

# Screen dimensions (fixed for mobile)
SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920  # Vertical mobile

# ---------- PROCESS ----------
if st.button("🎬 Create Mobile Video", type="primary", use_container_width=True) and background_file and overlay_file:

    with st.spinner("Creating your mobile video..."):
        
        # Save uploaded files with progress
        st.info("📁 Saving uploaded files...")
        
        def save_temp(upload):
            """Save uploaded file to temp location"""
            try:
                # Create temp file with proper extension
                suffix = os.path.splitext(upload.name)[1]
                if not suffix:
                    # Default extensions based on type
                    if upload.type.startswith('image'):
                        suffix = '.jpg'
                    elif upload.type.startswith('video'):
                        suffix = '.mp4'
                    elif upload.type.startswith('audio'):
                        suffix = '.mp3'
                
                f = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                f.write(upload.read())
                f.close()
                return f.name
            except Exception as e:
                st.error(f"Error saving file: {str(e)}")
                return None
        
        bg_path = save_temp(background_file)
        overlay_path = save_temp(overlay_file)
        
        if not bg_path or not overlay_path:
            st.error("Failed to save uploaded files")
            st.stop()
        
        FPS = 30
        
        try:
            # ----- STEP 1: EXTRACT AUDIO -----
            st.info("🎵 Extracting audio...")
            
            audio_clip = None
            # Try different methods to load audio
            try:
                # First try as video file
                if background_file.type.startswith('video') or bg_path.endswith(('.mp4', '.mov', '.avi')):
                    video_clip = VideoFileClip(bg_path)
                    audio_clip = video_clip.audio
                    video_clip.close()
                    
                    if audio_clip is None:
                        st.warning("No audio in video, trying as audio file...")
                        audio_clip = AudioFileClip(bg_path)
                else:
                    # Try as audio file
                    audio_clip = AudioFileClip(bg_path)
            except:
                st.error("Could not load audio from file")
                st.stop()
            
            if audio_clip is None:
                st.error("No audio found in the file!")
                st.stop()
            
            audio_duration = audio_clip.duration
            st.info(f"✅ Audio loaded: {audio_duration:.1f} seconds")
            
            # ----- STEP 2: PROCESS OVERLAY (IMAGE OR VIDEO) -----
            st.info("🖼️ Processing screen content...")
            
            # Check file type
            is_image = overlay_file.type.startswith('image') or overlay_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
            
            if is_image:
                # ----- IMAGE PROCESSING -----
                try:
                    # Open image
                    img = Image.open(overlay_path)
                    img_width, img_height = img.size
                    st.info(f"Image size: {img_width}×{img_height}")
                    
                    # Calculate aspect ratios
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT  # 0.5625 for 9:16
                    img_ratio = img_width / img_height
                    
                    # Crop image to fit mobile screen
                    if img_ratio > screen_ratio:
                        # Image is wider than screen - crop sides
                        new_height = img_height
                        new_width = int(img_height * screen_ratio)
                        left = (img_width - new_width) // 2
                        right = left + new_width
                        img = img.crop((left, 0, right, new_height))
                        st.info(f"Cropped sides: {new_width}×{new_height}")
                    else:
                        # Image is taller than screen - crop top/bottom
                        new_width = img_width
                        new_height = int(img_width / screen_ratio)
                        top = (img_height - new_height) // 2
                        bottom = top + new_height
                        img = img.crop((0, top, new_width, bottom))
                        st.info(f"Cropped top/bottom: {new_width}×{new_height}")
                    
                    # Resize to exact screen size
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                    
                    # Convert to RGB if needed (for JPG compatibility)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save processed image
                    temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg').name
                    img.save(temp_img_path, 'JPEG', quality=95)
                    
                    # Create ImageClip - SIMPLE WAY
                    try:
                        # Method 1: Try direct ImageClip creation
                        overlay = ImageClip(temp_img_path)
                    except:
                        # Method 2: Try with numpy array
                        img_array = np.array(img)
                        overlay = ImageClip(img_array)
                    
                    # Set duration to match audio
                    overlay = overlay.set_duration(audio_duration)
                    st.info("✅ Image processed successfully")
                    
                except Exception as img_error:
                    st.error(f"Error processing image: {str(img_error)}")
                    # Create fallback color clip
                    overlay = ColorClip((SCREEN_WIDTH, SCREEN_HEIGHT), color=(50, 50, 100), duration=audio_duration)
                    st.info("Using fallback background")
                    
            else:
                # ----- VIDEO PROCESSING -----
                try:
                    overlay = VideoFileClip(overlay_path)
                    orig_width, orig_height = overlay.size
                    st.info(f"Video: {orig_width}×{orig_height}, {overlay.duration:.1f}s")
                    
                    # Calculate aspect ratios
                    screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                    video_ratio = orig_width / orig_height
                    
                    # Crop video to fit mobile screen
                    if video_ratio > screen_ratio:
                        # Video is wider - crop sides
                        crop_width = int(orig_height * screen_ratio)
                        x_center = orig_width // 2
                        overlay = overlay.crop(x1=x_center - crop_width//2, 
                                              x2=x_center + crop_width//2)
                        st.info(f"Cropped video width to {crop_width}")
                    else:
                        # Video is taller - crop top/bottom
                        crop_height = int(orig_width / screen_ratio)
                        y_center = orig_height // 2
                        overlay = overlay.crop(y1=y_center - crop_height//2,
                                              y2=y_center + crop_height//2)
                        st.info(f"Cropped video height to {crop_height}")
                    
                    # Resize to screen size
                    overlay = overlay.resize((SCREEN_WIDTH, SCREEN_HEIGHT))
                    
                    # Handle duration
                    if overlay.duration < audio_duration:
                        # Loop video
                        loops = int(audio_duration // overlay.duration) + 1
                        overlay = concatenate_videoclips([overlay] * loops)
                        overlay = overlay.subclip(0, audio_duration)
                        st.info(f"Looped video {loops} times")
                    elif overlay.duration > audio_duration:
                        overlay = overlay.subclip(0, audio_duration)
                        st.info("Trimmed video to audio length")
                        
                    st.info("✅ Video processed successfully")
                    
                except Exception as vid_error:
                    st.error(f"Error processing video: {str(vid_error)}")
                    # Create fallback
                    overlay = ColorClip((SCREEN_WIDTH, SCREEN_HEIGHT), color=(100, 50, 50), duration=audio_duration)
                    st.info("Using fallback video")
            
            # ----- STEP 3: ADD AUDIO AND FINALIZE -----
            st.info("🎥 Adding audio to video...")
            
            # Make sure overlay is valid
            if overlay is None:
                st.error("Failed to create video content")
                st.stop()
            
            # Add audio
            try:
                final_video = overlay.set_audio(audio_clip)
                final_video = final_video.set_duration(audio_duration)
                final_video = final_video.set_fps(FPS)
            except Exception as audio_error:
                st.error(f"Error adding audio: {str(audio_error)}")
                st.stop()
            
            # ----- STEP 4: SAVE VIDEO -----
            st.info("💾 Saving video file...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
            
            # Simple write without complex options
            try:
                final_video.write_videofile(
                    output_path,
                    fps=FPS,
                    audio_codec='aac',
                    verbose=False,
                    logger=None
                )
            except Exception as write_error:
                st.error(f"Error saving video: {str(write_error)}")
                # Try alternative method
                try:
                    final_video.write_videofile(
                        output_path,
                        fps=FPS,
                        verbose=False
                    )
                except:
                    st.error("Failed to save video file")
                    st.stop()
            
            # Cleanup temp files
            temp_files = [bg_path, overlay_path]
            if 'temp_img_path' in locals():
                temp_files.append(temp_img_path)
            
            for file_path in temp_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            st.success("✅ Mobile video created successfully!")
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ Error creating video: {str(e)}")
            st.stop()
    
    # ----- STEP 5: SHOW AND DOWNLOAD -----
    st.subheader("📱 Your Mobile Video")
    
    # Show video preview
    if os.path.exists(output_path):
        try:
            st.video(output_path)
        except:
            st.info("Video preview available for download")
        
        # Show video info
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Screen Size", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
            st.metric("Duration", f"{audio_duration:.1f}s")
        with col2:
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            st.metric("File Size", f"{file_size:.1f} MB")
            st.metric("Format", "MP4")
        
        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "⬇ Download Video",
                f,
                file_name="mobile_video.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
    else:
        st.error("Video file was not created successfully")

else:
    # Show instructions when no files uploaded
    st.info("👆 Upload files to create a mobile video")
    
    st.markdown("""
    ### 📝 Simple Instructions:
    
    1. **Upload Background Music** (required):
       - Audio file: MP3, WAV, M4A, AAC
       - Video file: MP4, MOV, AVI (audio will be extracted)
    
    2. **Upload Screen Content** (required):
       - Image: PNG, JPG, JPEG
       - Video: MP4, MOV, AVI
    
    3. **Click "Create Mobile Video"**
    
    ### ✨ What you get:
    - Vertical video (1080×1920)
    - Full screen content (no borders)
    - Your audio playing
    - MP4 format ready to share
    """)

# Cleanup function for output file
@st.cache_resource(ttl=600)
def cleanup_output_files():
    """Clean up output files after 10 minutes"""
    pass
