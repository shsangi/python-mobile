import streamlit as st
import tempfile
import os
import gc
import subprocess
from PIL import Image
import base64

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    CompositeVideoClip
)

my_title = "🎬 Mobile Video Maker V 22"  # Updated version

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title=my_title,
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
    /* Better video display */
    .stVideo {
        border-radius: 10px;
        overflow: hidden;
        background-color: black;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - Optimized for mobile")

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
    'overlay_size': None,
    'bg_size': None
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- ENHANCED HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def get_video_info(video_path):
    """Get detailed video information"""
    try:
        # Use ffprobe to get accurate video info
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,codec_name,pix_fmt,duration',
            '-of', 'json',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout
    except:
        return None

def show_single_frame_preview(video_path, time_point=1):
    """Show a single frame from video"""
    try:
        clip = VideoFileClip(video_path, audio=False, fps_source='fps')
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        img.thumbnail((300, 300))
        
        clip.close()
        return img
    except Exception as e:
        st.warning(f"Preview error: {str(e)}")
        return None

def optimize_for_mobile(input_path, output_path):
    """Optimize video for mobile playback"""
    cmd = [
        'ffmpeg', '-y',
        '-i', input_path,
        '-c:v', 'libx264',
        '-profile:v', 'high',
        '-level', '4.2',  # Support for most mobile devices
        '-pix_fmt', 'yuv420p',  # Essential for iPhone/Android compatibility
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',  # Enable streaming
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Ensure even dimensions
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Optimization failed: {e.stderr.decode()}")
        return False

def validate_video_compatibility(video_path):
    """Check if video is compatible with mobile devices"""
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=pix_fmt',
            '-of', 'csv=p=0',
            video_path
        ]
        pix_fmt = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        
        # Check for compatible pixel format
        compatible_formats = ['yuv420p', 'yuvj420p', 'yuv422p', 'yuv444p']
        if pix_fmt not in compatible_formats:
            return False, f"Incompatible pixel format: {pix_fmt}. Needs yuv420p for mobile."
        
        return True, f"Compatible format: {pix_fmt}"
    except:
        return True, "Could not verify format"  # Assume OK if can't check

# ---------- UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a", "wav", "avi"],
        help="Audio will be extracted from this file. Max 100MB"
    )
    
    if background_file:
        if background_file.size > 100 * 1024 * 1024:  # 100MB limit
            st.error("File too large! Max 100MB")
            st.stop()
            
        if st.session_state.prev_bg_file != background_file.name:
            if st.session_state.bg_clip:
                try:
                    st.session_state.bg_clip.close()
                except:
                    pass
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save and load
        with st.spinner("Loading background..."):
            st.session_state.bg_path = save_uploaded_file(background_file)
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi']
            
            try:
                if st.session_state.bg_is_video:
                    # Load with specific parameters
                    st.session_state.bg_clip = VideoFileClip(
                        st.session_state.bg_path, 
                        audio=True,
                        fps_source='fps',
                        target_resolution=None
                    )
                    if st.session_state.bg_clip.audio:
                        st.session_state.bg_duration = st.session_state.bg_clip.audio.duration
                        st.success(f"✅ Video: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                        # Store video dimensions
                        st.session_state.bg_size = st.session_state.bg_clip.size
                    else:
                        st.error("No audio in video")
                        st.stop()
                else:
                    # Audio file
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                    st.success(f"✅ Audio: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
                
            except Exception as e:
                st.error(f"Error loading file: {str(e)}")
                with st.expander("Technical details"):
                    st.code(str(e))

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov", "avi", "mkv"],
        help="Video overlay. Will be centered. Max 100MB"
    )
    
    if overlay_file:
        if overlay_file.size > 100 * 1024 * 1024:  # 100MB limit
            st.error("File too large! Max 100MB")
            st.stop()
            
        if st.session_state.prev_overlay_file != overlay_file.name:
            if st.session_state.overlay_clip:
                try:
                    st.session_state.overlay_clip.close()
                except:
                    pass
            st.session_state.overlay_clip = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save and load
        with st.spinner("Loading overlay..."):
            st.session_state.overlay_path = save_uploaded_file(overlay_file)
            st.session_state.overlay_is_image = False
            
            try:
                # Check compatibility
                is_compatible, message = validate_video_compatibility(st.session_state.overlay_path)
                if not is_compatible:
                    st.warning(message)
                
                # Load overlay video
                st.session_state.overlay_clip = VideoFileClip(
                    st.session_state.overlay_path, 
                    audio=False,
                    fps_source='fps',
                    target_resolution=None
                )
                st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                
                # Store overlay dimensions
                st.session_state.overlay_size = st.session_state.overlay_clip.size
                
                st.success(f"✅ Overlay: {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
                st.info(f"Resolution: {st.session_state.overlay_size[0]}×{st.session_state.overlay_size[1]}")
                
                # Show preview
                preview_img = show_single_frame_preview(st.session_state.overlay_path)
                if preview_img:
                    st.image(preview_img, caption="Overlay preview", use_column_width=True)
                    
            except Exception as e:
                st.error(f"Error loading overlay: {str(e)}")
                with st.expander("Technical details"):
                    st.code(str(e))

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Audio Settings**")
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

if st.session_state.overlay_duration > 0:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Video Settings**")
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
    st.info(f"📹 Video: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")

# ---------- VIDEO POSITIONING OPTIONS ----------
if st.session_state.overlay_size:
    st.subheader("🎯 Overlay Position")
    
    position_options = {
        "Center": "center",
        "Top Left": "top_left",
        "Top Right": "top_right",
        "Bottom Left": "bottom_left",
        "Bottom Right": "bottom_right"
    }
    
    selected_position = st.selectbox(
        "Position overlay video",
        options=list(position_options.keys()),
        index=0
    )
    
    # Calculate position based on selection
    position = position_options[selected_position]

# ---------- ENHANCED PROCESS FUNCTION ----------
def process_video_mobile_optimized():
    """Combine audio and video with mobile optimization"""
    try:
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 30)
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration', 30)
        overlay_end = overlay_start + overlay_duration_val
        
        # Get position
        selected_position = st.session_state.get('selected_position', 'center')
        
        # Extract audio
        with st.spinner("🎵 Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video
        with st.spinner("📹 Processing video..."):
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
            
            # Calculate position for overlay
            overlay_width, overlay_height = overlay.size
            
            # Create a background if needed (for positioning)
            # Use black background with same dimensions as overlay
            from moviepy.editor import ColorClip
            
            # Create background same size as overlay
            background = ColorClip(
                size=overlay.size,
                color=(0, 0, 0),  # Black background
                duration=overlay.duration
            )
            
            # Composite overlay on background (centered by default)
            final_video = CompositeVideoClip([background, overlay.set_position('center')])
            
            # Add audio
            final_video = final_video.set_audio(audio_clip)
            final_video = final_video.set_duration(final_audio_duration)
        
        # Save initial video
        with st.spinner("💾 Saving video..."):
            temp_output = tempfile.NamedTemporaryFile(delete=False, suffix="_temp.mp4").name
            final_output = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
            
            # Write with proper parameters
            final_video.write_videofile(
                temp_output,
                fps=overlay.fps,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="128k",
                bitrate="5000k",
                preset='medium',
                threads=4,
                ffmpeg_params=['-movflags', '+faststart', '-pix_fmt', 'yuv420p']
            )
        
        # Optimize for mobile
        with st.spinner("📱 Optimizing for mobile..."):
            if optimize_for_mobile(temp_output, final_output):
                output_path = final_output
            else:
                output_path = temp_output
                st.warning("Using unoptimized version")
        
        # Get final video info
        from moviepy.editor import VideoFileClip
        final_clip = VideoFileClip(output_path)
        width, height = final_clip.size
        duration = final_clip.duration
        final_clip.close()
        
        # Cleanup
        try:
            audio_clip.close()
            overlay.close()
            final_video.close()
            background.close()
        except:
            pass
        
        # Remove temp file
        if os.path.exists(temp_output):
            os.unlink(temp_output)
        
        return output_path, duration, width, height
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        import traceback
        with st.expander("🔧 Error details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0

# ---------- CREATE BUTTON ----------
st.divider()

# Check if both files are uploaded
files_ready = st.session_state.bg_path and st.session_state.overlay_path

create_col1, create_col2 = st.columns([3, 1])

with create_col1:
    if st.button("🎬 Create Final Video", 
                 type="primary", 
                 disabled=not files_ready,
                 use_container_width=True):
        
        if not files_ready:
            st.warning("Please upload both background and overlay files first")
            st.stop()
        
        # Show progress
        progress_bar = st.progress(0)
        
        # Process video
        output_path, duration, width, height = process_video_mobile_optimized()
        progress_bar.progress(100)
        
        if output_path and os.path.exists(output_path):
            st.success("✅ Video created successfully!")
            
            # Show video with better styling
            st.subheader("🎥 Your Video Preview")
            
            # Display video
            try:
                video_file = open(output_path, 'rb')
                video_bytes = video_file.read()
                video_file.close()
                
                # Use HTML5 video tag for better control
                st.video(video_bytes)
            except Exception as e:
                st.warning(f"Preview not available: {str(e)}")
                st.info("Video will download correctly")
            
            # Show info in cards
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Duration", f"{duration:.1f}s")
            with col2:
                st.metric("Resolution", f"{width}×{height}")
            with col3:
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                st.metric("File Size", f"{file_size:.1f} MB")
            
            # Download button
            st.divider()
            st.subheader("📥 Download")
            
            with open(output_path, "rb") as f:
                st.download_button(
                    "📥 Download Video",
                    f,
                    file_name=f"mobile_video_{width}x{height}.mp4",
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True
                )
            
            # Cleanup instructions
            st.info("💡 **Tip:** If video doesn't play on mobile, try using VLC Player or MX Player")
        
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

with create_col2:
    if st.button("🔄 Clear All", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key != 'prev_bg_file' and key != 'prev_overlay_file':
                st.session_state[key] = None
        gc.collect()
        st.rerun()

# ---------- TROUBLESHOOTING SECTION ----------
with st.expander("🔧 Troubleshooting Common Issues"):
    st.markdown("""
    ### Common Issues & Solutions:
    
    **1. Video doesn't play on iPhone/Android:**
    - Ensure pixel format is `yuv420p` (our code forces this)
    - Add `-movflags +faststart` for streaming
    - Use H.264 codec with AAC audio
    
    **2. Overlay not showing:**
    - Check if overlay video has valid frames
    - Try different start time (some videos have blank start)
    - Ensure video is not corrupted
    
    **3. Audio/video sync issues:**
    - Use same FPS for all clips
    - Avoid very short clips (< 1 second)
    - Check original file compatibility
    
    **4. Large file sizes:**
    - We optimize with CRF 23 (good quality/size balance)
    - Consider shorter durations
    - Original resolution affects size
    
    **5. Black screen on mobile:**
    - Ensure dimensions are even numbers (divisible by 2)
    - Check codec compatibility
    - Try different player app
    
    **Need more help?** Try re-encoding your source videos with HandBrake using "Fast 1080p30" preset.
    """)

# ---------- HOW TO USE ----------
with st.expander("📖 How to Use This Tool"):
    st.markdown("""
    ### Mobile Video Creator Guide
    
    **Step-by-Step:**
    1. **Upload Background** - Audio or video file
    2. **Upload Overlay** - Video file to display
    3. **Trim Both** - Set start times and durations
    4. **Set Position** - Choose where overlay appears
    5. **Click Create** - Generate mobile-optimized video
    
    **Features:**
    - ✅ Mobile-optimized output
    - ✅ No resizing (keeps original quality)
    - ✅ Audio extraction from videos
    - ✅ Loop short videos to match audio
    - ✅ Multiple position options
    - ✅ Fast streaming (moov atom at start)
    
    **Best Practices:**
    - Use MP4 files when possible
    - Keep videos under 5 minutes for best results
    - 1080p or 720p recommended
    - Stereo audio works best
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("📱 Mobile Video Maker • Version 22 • Optimized for all devices")
