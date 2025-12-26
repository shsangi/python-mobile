import streamlit as st
import tempfile
import os
import subprocess
from PIL import Image
import time

# Add version tracking
VERSION = "3.3.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Mobile Video Maker", layout="centered")
st.title(f"📱 Mobile Video Maker v{VERSION}")
st.markdown("Create mobile videos that fill the entire screen")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
App Version     : {VERSION}
Python          : {os.sys.version}
""")

# ---------- UPLOADS ----------
col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Music/Audio",
        type=["mp3", "wav", "m4a", "mp4", "mov"],
        help="Upload audio or video file"
    )

with col2:
    overlay_file = st.file_uploader(
        "Screen Content (Image or Video)",
        type=["mp4", "mov", "png", "jpg", "jpeg"],
        help="Upload image or video"
    )

# Screen dimensions
SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920

# Initialize session state
if 'audio_range' not in st.session_state:
    st.session_state.audio_range = [0, 15]
if 'video_range' not in st.session_state:
    st.session_state.video_range = [0, 10]
if 'audio_duration' not in st.session_state:
    st.session_state.audio_duration = 0
if 'video_duration' not in st.session_state:
    st.session_state.video_duration = 0

# Function to get media duration
def get_media_duration(file_path, is_video=False):
    """Get duration of audio or video file using ffprobe"""
    try:
        if is_video:
            cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-show_entries', 'stream=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', file_path
            ]
        else:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 
                'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', file_path
            ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        return duration
    except:
        return 30.0  # Default fallback

# Function to create thumbnail
def create_thumbnail(file_path, time_point, output_path, is_video=True):
    """Create thumbnail at specific time"""
    try:
        if is_video:
            cmd = [
                'ffmpeg',
                '-ss', str(time_point),
                '-i', file_path,
                '-vframes', '1',
                '-vf', 'scale=320:-1',
                '-y',
                output_path
            ]
        else:
            # For audio, create waveform image
            cmd = [
                'ffmpeg',
                '-ss', str(time_point),
                '-i', file_path,
                '-t', '2',
                '-filter_complex', 
                '[0:a]showwaves=s=320x240:mode=line:colors=#1f77b4,format=rgba[v]',
                '-map', '[v]',
                '-y',
                output_path
            ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

# Function to create range preview
def create_range_preview(file_path, start_time, end_time, output_path, is_video=True):
    """Create preview of selected range"""
    try:
        duration = end_time - start_time
        preview_duration = min(duration, 10)  # Max 10 seconds preview
        
        if is_video:
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', file_path,
                '-t', str(preview_duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-vf', 'scale=640:-1',
                '-y',
                output_path
            ]
        else:
            # For audio, create video with waveform
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', file_path,
                '-t', str(preview_duration),
                '-filter_complex', 
                '[0:a]showwaves=s=640x240:mode=line:colors=white:scale=sqrt,format=rgba[v]',
                '-map', '[v]',
                '-y',
                output_path
            ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except:
        return False

# Custom CSS for better slider styling
st.markdown("""
<style>
/* Style for range slider labels */
div[data-testid="stSlider"] label {
    font-weight: bold !important;
}

/* Style for preview container */
.preview-container {
    border: 2px solid #4CAF50;
    border-radius: 10px;
    padding: 15px;
    margin: 10px 0;
    background-color: #f8f9fa;
}

.range-info {
    background-color: #e8f4fd;
    padding: 10px;
    border-radius: 5px;
    margin: 10px 0;
}

.slider-header {
    font-size: 1.2em;
    font-weight: bold;
    color: #1f77b4;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# Audio trimming options with range slider
if background_file:
    st.subheader("🎵 Audio Settings")
    with st.expander("✂️ Trim Background Audio", expanded=True):
        
        # Create temp file to get duration
        temp_dir = tempfile.mkdtemp()
        temp_audio_path = os.path.join(temp_dir, "temp_audio" + os.path.splitext(background_file.name)[1])
        
        with open(temp_audio_path, "wb") as f:
            f.write(background_file.getbuffer())
        
        # Get audio duration
        audio_duration = get_media_duration(temp_audio_path, is_video=False)
        st.session_state.audio_duration = audio_duration
        
        st.info(f"🎵 Total Audio Length: **{audio_duration:.1f} seconds**")
        
        # Range slider for audio
        st.markdown('<div class="slider-header">🎚️ Select Audio Range</div>', unsafe_allow_html=True)
        audio_range = st.slider(
            "Drag the handles to select start and end points",
            min_value=0.0,
            max_value=float(audio_duration),
            value=(float(st.session_state.audio_range[0]), 
                   float(min(audio_duration, st.session_state.audio_range[1]))),
            step=0.1,
            format="%.1f s",
            key="audio_range_slider",
            label_visibility="collapsed"
        )
        
        st.session_state.audio_range = list(audio_range)
        audio_start, audio_end = audio_range
        audio_duration_selected = audio_end - audio_start
        
        # Show range info
        st.markdown(f"""
        <div class="range-info">
        📊 **Selected Range:** {audio_start:.1f}s to {audio_end:.1f}s
        <br>
        ⏱️ **Duration:** {audio_duration_selected:.1f} seconds
        </div>
        """, unsafe_allow_html=True)
        
        # Create and show preview
        st.markdown('<div class="slider-header">🎧 Audio Preview</div>', unsafe_allow_html=True)
        preview_path = os.path.join(temp_dir, "audio_preview.mp4")
        
        # Create preview on slider change
        if create_range_preview(temp_audio_path, audio_start, audio_end, preview_path, is_video=False):
            if os.path.exists(preview_path):
                try:
                    with open(preview_path, "rb") as f:
                        video_bytes = f.read()
                        st.video(video_bytes, format="video/mp4", start_time=0)
                except:
                    st.info("Audio preview generated. Adjust sliders to change preview.")
            else:
                st.info("Adjust sliders to generate preview")
        else:
            st.info("Drag slider handles to select audio segment")
        
        # Info metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Start", f"{audio_start:.1f}s")
        with col2:
            st.metric("End", f"{audio_end:.1f}s")
        with col3:
            st.metric("Duration", f"{audio_duration_selected:.1f}s")
        
        # Clean up temp directory
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

# Overlay video trimming with range slider
if overlay_file:
    is_image = overlay_file.type.startswith('image') or overlay_file.name.lower().endswith(('.png', '.jpg', '.jpeg'))
    
    if not is_image:
        st.subheader("🎬 Overlay Video Settings")
        with st.expander("✂️ Trim Overlay Video", expanded=True):
            
            # Create temp file to get duration
            temp_dir = tempfile.mkdtemp()
            temp_video_path = os.path.join(temp_dir, "temp_video" + os.path.splitext(overlay_file.name)[1])
            
            with open(temp_video_path, "wb") as f:
                f.write(overlay_file.getbuffer())
            
            # Get video duration
            video_duration = get_media_duration(temp_video_path, is_video=True)
            st.session_state.video_duration = video_duration
            
            st.info(f"🎬 Total Video Length: **{video_duration:.1f} seconds**")
            
            # Range slider for video
            st.markdown('<div class="slider-header">🎚️ Select Video Range</div>', unsafe_allow_html=True)
            video_range = st.slider(
                "Drag the handles to select start and end points",
                min_value=0.0,
                max_value=float(video_duration),
                value=(float(st.session_state.video_range[0]), 
                       float(min(video_duration, st.session_state.video_range[1]))),
                step=0.1,
                format="%.1f s",
                key="video_range_slider",
                label_visibility="collapsed"
            )
            
            st.session_state.video_range = list(video_range)
            video_start, video_end = video_range
            video_duration_selected = video_end - video_start
            
            # Show range info
            st.markdown(f"""
            <div class="range-info">
            📊 **Selected Range:** {video_start:.1f}s to {video_end:.1f}s
            <br>
            ⏱️ **Duration:** {video_duration_selected:.1f} seconds
            </div>
            """, unsafe_allow_html=True)
            
            # Create thumbnails for start and end points
            st.markdown('<div class="slider-header">📸 Frame Previews</div>', unsafe_allow_html=True)
            col_start, col_end = st.columns(2)
            
            with col_start:
                st.markdown("**Start Frame**")
                thumbnail_start = os.path.join(temp_dir, "thumbnail_start.jpg")
                if create_thumbnail(temp_video_path, video_start, thumbnail_start, is_video=True):
                    st.image(thumbnail_start, use_column_width=True, caption=f"At {video_start:.1f}s")
            
            with col_end:
                st.markdown("**End Frame**")
                thumbnail_end = os.path.join(temp_dir, "thumbnail_end.jpg")
                if create_thumbnail(temp_video_path, video_end - 0.1, thumbnail_end, is_video=True):
                    st.image(thumbnail_end, use_column_width=True, caption=f"At {video_end:.1f}s")
            
            # Create and show video preview
            st.markdown('<div class="slider-header">🎬 Video Preview</div>', unsafe_allow_html=True)
            preview_path = os.path.join(temp_dir, "video_preview.mp4")
            
            # Create preview on slider change
            if create_range_preview(temp_video_path, video_start, video_end, preview_path, is_video=True):
                if os.path.exists(preview_path):
                    try:
                        with open(preview_path, "rb") as f:
                            video_bytes = f.read()
                            st.video(video_bytes, format="video/mp4", start_time=0)
                    except:
                        st.info("Video preview generated. Adjust sliders to change preview.")
                else:
                    st.info("Adjust sliders to generate preview")
            else:
                st.info("Drag slider handles to select video segment")
            
            # Info metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Start", f"{video_start:.1f}s")
            with col2:
                st.metric("End", f"{video_end:.1f}s")
            with col3:
                st.metric("Duration", f"{video_duration_selected:.1f}s")
            
            # Clean up temp directory
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    else:
        # For images, set default values
        video_start = 0.0
        video_duration_selected = None

# ---------- PROCESS USING FFMPEG DIRECTLY ----------
if st.button("🎬 Create Mobile Video", type="primary", use_container_width=True) and background_file and overlay_file:

    with st.spinner("Creating your mobile video..."):
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # ----- STEP 1: SAVE FILES -----
            st.info("📁 Preparing files...")
            
            bg_path = os.path.join(temp_dir, "background" + os.path.splitext(background_file.name)[1])
            with open(bg_path, "wb") as f:
                f.write(background_file.getbuffer())
            
            overlay_path = os.path.join(temp_dir, "overlay" + os.path.splitext(overlay_file.name)[1])
            with open(overlay_path, "wb") as f:
                f.write(overlay_file.getbuffer())
            
            output_path = os.path.join(temp_dir, "output.mp4")
            
            # ----- STEP 2: CHECK FILE TYPES -----
            is_image = overlay_file.type.startswith('image') or overlay_path.lower().endswith(('.png', '.jpg', '.jpeg'))
            
            # Get selected audio duration
            audio_start, audio_end = st.session_state.audio_range
            audio_duration_selected = audio_end - audio_start
            
            # Validate audio range
            if audio_start >= st.session_state.audio_duration:
                st.error(f"Audio start time ({audio_start}s) exceeds audio length ({st.session_state.audio_duration:.1f}s)")
                st.stop()
            
            if is_image:
                # ----- PROCESS IMAGE WITH FFMPEG -----
                st.info("🖼️ Processing image...")
                
                # First, resize image to mobile dimensions
                resized_image = os.path.join(temp_dir, "resized_image.jpg")
                
                # Use PIL to resize image
                img = Image.open(overlay_path)
                img_width, img_height = img.size
                
                # Calculate cropping
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                img_ratio = img_width / img_height
                
                if img_ratio > screen_ratio:
                    # Crop sides
                    new_height = img_height
                    new_width = int(img_height * screen_ratio)
                    left = (img_width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, new_height))
                else:
                    # Crop top/bottom
                    new_width = img_width
                    new_height = int(img_width / screen_ratio)
                    top = (img_height - new_height) // 2
                    img = img.crop((0, top, new_width, top + new_height))
                
                # Resize to exact dimensions
                img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.Resampling.LANCZOS)
                img.save(resized_image, "JPEG", quality=95)
                
                # Create video from image with trimmed audio using ffmpeg
                st.info("🎥 Creating video from image...")
                
                cmd = [
                    'ffmpeg',
                    '-loop', '1',  # Loop the image
                    '-i', resized_image,  # Input image
                    '-ss', str(audio_start),  # Audio start time
                    '-i', bg_path,  # Input audio
                    '-c:v', 'libx264',  # Video codec
                    '-c:a', 'aac',  # Audio codec
                    '-b:a', '192k',  # Audio bitrate
                    '-vf', f'scale={SCREEN_WIDTH}:{SCREEN_HEIGHT}:force_original_aspect_ratio=decrease,pad={SCREEN_WIDTH}:{SCREEN_HEIGHT}:(ow-iw)/2:(oh-ih)/2',  # Scale and pad
                    '-pix_fmt', 'yuv420p',  # Pixel format
                    '-shortest',  # End when audio ends
                    '-t', str(audio_duration_selected),  # Duration from trimmed audio
                    '-y',  # Overwrite output
                    output_path
                ]
                
            else:
                # ----- PROCESS VIDEO WITH FFMPEG -----
                st.info("🎬 Processing video...")
                
                # Get selected video duration
                video_start, video_end = st.session_state.video_range
                video_duration_selected = video_end - video_start
                
                # Validate video range
                if video_start >= st.session_state.video_duration:
                    st.error(f"Video start time ({video_start}s) exceeds video length ({st.session_state.video_duration:.1f}s)")
                    st.stop()
                
                # First, get video info
                try:
                    cmd = [
                        'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                        '-show_entries', 'stream=width,height',
                        '-of', 'csv=p=0', overlay_path
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    width, height = result.stdout.strip().split(',')
                    width, height = int(width), int(height)
                except:
                    width, height = 480, 848
                
                st.info(f"📊 Video: {width}×{height}, Audio: {audio_duration_selected:.1f}s, Video: {video_duration_selected:.1f}s")
                
                # Calculate cropping for mobile
                screen_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
                video_ratio = width / height
                
                # Create filter for cropping and scaling
                if abs(video_ratio - screen_ratio) < 0.1:
                    # Already mobile aspect, just resize
                    filter_complex = f"scale={SCREEN_WIDTH}:{SCREEN_HEIGHT}"
                elif video_ratio > screen_ratio:
                    # Wider than mobile, crop sides
                    crop_width = int(height * screen_ratio)
                    crop_x = (width - crop_width) // 2
                    filter_complex = f"crop={crop_width}:{height}:{crop_x}:0,scale={SCREEN_WIDTH}:{SCREEN_HEIGHT}"
                else:
                    # Taller than mobile, crop top/bottom
                    crop_height = int(width / screen_ratio)
                    crop_y = (height - crop_height) // 2
                    filter_complex = f"crop={width}:{crop_height}:0:{crop_y},scale={SCREEN_WIDTH}:{SCREEN_HEIGHT}"
                
                # Determine which duration to use (shortest between audio and video)
                final_duration = min(audio_duration_selected, video_duration_selected)
                
                # Handle video duration - loop if video is shorter than needed
                if video_duration_selected < final_duration:
                    # Need to loop video
                    loop_count = int(final_duration // video_duration_selected) + 1
                    
                    # First create trimmed video segment
                    trimmed_video = os.path.join(temp_dir, "trimmed_video.mp4")
                    cmd_trim = [
                        'ffmpeg',
                        '-ss', str(video_start),  # Video start time
                        '-i', overlay_path,  # Input video
                        '-t', str(video_duration_selected),  # Video duration
                        '-c', 'copy',  # Copy without re-encoding
                        '-y',
                        trimmed_video
                    ]
                    subprocess.run(cmd_trim, capture_output=True)
                    
                    # Create file with list of videos to concatenate
                    concat_list = os.path.join(temp_dir, "concat_list.txt")
                    with open(concat_list, "w") as f:
                        for _ in range(loop_count):
                            f.write(f"file '{trimmed_video}'\n")
                    
                    # Create looped video
                    looped_video = os.path.join(temp_dir, "looped.mp4")
                    cmd_loop = [
                        'ffmpeg',
                        '-f', 'concat',
                        '-safe', '0',
                        '-i', concat_list,
                        '-c', 'copy',
                        '-t', str(final_duration),
                        '-y',
                        looped_video
                    ]
                    
                    subprocess.run(cmd_loop, capture_output=True)
                    
                    # Use looped video as input
                    input_video = looped_video
                else:
                    # Just trim the video if needed
                    if video_start > 0 or video_duration_selected < st.session_state.video_duration:
                        trimmed_video = os.path.join(temp_dir, "trimmed_video.mp4")
                        cmd_trim = [
                            'ffmpeg',
                            '-ss', str(video_start),  # Video start time
                            '-i', overlay_path,  # Input video
                            '-t', str(final_duration),  # Video duration limit
                            '-c', 'copy',  # Copy without re-encoding
                            '-y',
                            trimmed_video
                        ]
                        subprocess.run(cmd_trim, capture_output=True)
                        input_video = trimmed_video
                    else:
                        input_video = overlay_path
                
                # Create final video with ffmpeg
                st.info("🎥 Creating final video...")
                
                cmd = [
                    'ffmpeg',
                    '-i', input_video,  # Input video (already trimmed/looped)
                    '-ss', str(audio_start),  # Audio start time
                    '-i', bg_path,  # Input audio
                    '-filter_complex', f'[0:v]{filter_complex}[v]',  # Video filter
                    '-map', '[v]',  # Map video stream
                    '-map', '1:a',  # Map audio stream
                    '-c:v', 'libx264',  # Video codec
                    '-c:a', 'aac',  # Audio codec
                    '-b:a', '192k',  # Audio bitrate
                    '-pix_fmt', 'yuv420p',  # Pixel format
                    '-shortest',  # End when shortest stream ends
                    '-t', str(final_duration),  # Use the determined duration
                    '-y',  # Overwrite output
                    output_path
                ]
            
            # ----- STEP 3: RUN FFMPEG -----
            st.info("⚡ Processing with FFmpeg...")
            
            # Run ffmpeg
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                st.error(f"FFmpeg error: {result.stderr}")
                st.stop()
            
            # ----- STEP 4: VERIFY OUTPUT -----
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                st.success("✅ Mobile video created successfully!")
                st.balloons()
            else:
                st.error("Failed to create video")
                st.stop()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 5: SHOW AND DOWNLOAD -----
    st.subheader("📱 Your Mobile Video")
    
    if os.path.exists(output_path):
        # Get file info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        # Show video
        try:
            st.video(output_path)
        except:
            st.info("🎬 Video created successfully!")
        
        # Show info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
        with col2:
            st.metric("File Size", f"{file_size:.1f} MB")
        with col3:
            st.metric("Duration", f"{final_duration if 'final_duration' in locals() else audio_duration_selected:.1f}s")
        
        # Download button
        with open(output_path, "rb") as f:
            st.download_button(
                "⬇ Download Mobile Video",
                f,
                file_name="mobile_video.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Clean up temp directory after download
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

else:
    # Show instructions
    st.info("👆 Upload files to create a mobile video")
    
    st.markdown("""
    ### 🎯 How it works:
    
    1. **Upload Background Audio**  
       - MP3, WAV, M4A (audio files)  
       - MP4, MOV (video files - audio will be extracted)
       - Use the range slider to select exact segment
       - See live preview as you adjust
    
    2. **Upload Screen Content**  
       - Image: PNG, JPG, JPEG (will fill screen)  
       - Video: MP4, MOV (will fill screen)
       - For videos: Use range slider to select exact segment
       - See frame previews and live video
    
    3. **Live Preview**  
       - Instant preview updates as you adjust sliders
       - See thumbnails at start/end points
       - Perfect your selection before final creation
    
    4. **Click Create**  
       Get a perfect mobile video
    
    ### ✨ Features:
    - **Range Sliders** - Single slider with two handles
    - **Live Previews** - Updates in real-time
    - **Full screen content** - No borders
    - **Vertical format** - 1080×1920
    - **Audio/Video trimming** - Select exact segments
    - **Fast processing** - Uses FFmpeg directly
    """)

# ---------- SIMPLE TIPS ----------
with st.expander("💡 Tips for best results"):
    st.markdown("""
    ### 🎚️ Using Range Sliders:
    
    **🎵 Audio Selection:**
    - Drag the **left handle** for start point
    - Drag the **right handle** for end point
    - See waveform preview update instantly
    - Maximum 5 minutes selection
    
    **🎬 Video Selection:**
    - See **frame previews** at start/end points
    - Live video preview updates as you adjust
    - Perfect for selecting exact clips
    
    **📱 Mobile Videos:**
    - Upload vertical videos (9:16 aspect)
    - Use MP4 format for best compatibility
    - Keep files under 100MB
    
    ### 🎯 Pro Tips:
    1. **Sync audio with video**: Match start points for better timing
    2. **Use live previews**: Adjust until preview looks perfect
    3. **Check frame previews**: Ensure good start/end frames
    4. **Short clips work best**: 15-60 seconds for social media
    """)
