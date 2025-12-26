import streamlit as st
import tempfile
import os
import gc
from PIL import Image
import base64
import subprocess
import numpy as np

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips,
    AudioArrayClip
)
from moviepy.config import change_settings

# Set FFMPEG path (adjust if needed)
change_settings({"FFMPEG_BINARY": "ffmpeg"})

my_title = "🎬 Mobile Video Maker V 2.1"
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
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    /* Info boxes */
    .info-box {
        padding: 10px;
        border-radius: 5px;
        background-color: #f0f2f6;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - No resizing - Mobile Optimized")

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
    'overlay_info': None
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

def validate_video_file(file_path):
    """Check if video file is compatible"""
    try:
        clip = VideoFileClip(file_path, audio=False)
        info = {
            'width': clip.w,
            'height': clip.h,
            'duration': clip.duration,
            'fps': clip.fps,
            'aspect_ratio': clip.w / clip.h,
            'is_portrait': clip.h > clip.w,
            'size': os.path.getsize(file_path) / (1024 * 1024)  # MB
        }
        clip.close()
        return info
    except Exception as e:
        st.warning(f"⚠️ Video validation warning: {str(e)}")
        return None

def convert_to_compatible_format(input_path):
    """Convert video to a more compatible format for mobile devices"""
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
    
    cmd = [
        'ffmpeg', '-i', input_path,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-pix_fmt', 'yuv420p',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',
        '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2',  # Ensure even dimensions
        '-y', output_path
    ]
    
    try:
        with st.spinner("Converting video for mobile compatibility..."):
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        st.success("✅ Video converted for mobile compatibility")
        return output_path
    except subprocess.CalledProcessError as e:
        st.warning(f"⚠️ Conversion failed: {e.stderr[:200]}")
        return input_path  # Return original if conversion fails
    except Exception as e:
        st.warning(f"⚠️ Conversion error: {str(e)}")
        return input_path

def display_video_with_fallback(video_path):
    """Display video with fallback for mobile compatibility"""
    try:
        # Display video
        video_bytes = open(video_path, 'rb').read()
        st.video(video_bytes)
        
        # Also show video info
        try:
            clip = VideoFileClip(video_path, audio=False)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Resolution", f"{clip.w}×{clip.h}")
            with col2:
                st.metric("FPS", f"{clip.fps:.1f}")
            with col3:
                st.metric("Duration", f"{clip.duration:.1f}s")
            clip.close()
        except:
            pass
            
    except Exception as e:
        st.warning("📱 Preview might not display in all browsers. Download to view on mobile.")
        
        # Fallback: show file info
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        st.info(f"Video file ready: {file_size:.1f}MB - Download to view")

# ---------- UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a", "wav", "avi"],
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
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi']
            
            try:
                if st.session_state.bg_is_video:
                    st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                    audio = st.session_state.bg_clip.audio
                    if audio:
                        st.session_state.bg_duration = audio.duration
                        st.success(f"✅ Video: {background_file.name}")
                        st.info(f"Duration: {st.session_state.bg_duration:.1f}s")
                    else:
                        st.error("❌ No audio in video")
                        st.stop()
                else:
                    audio = AudioFileClip(st.session_state.bg_path)
                    st.session_state.bg_duration = audio.duration
                    st.success(f"✅ Audio: {background_file.name}")
                    st.info(f"Duration: {st.session_state.bg_duration:.1f}s")
                
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        help="Video overlay (will not be resized). For best mobile compatibility, use MP4 format."
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
                # Validate video
                overlay_info = validate_video_file(st.session_state.overlay_path)
                
                if overlay_info:
                    st.session_state.overlay_info = overlay_info
                    
                    # Check for potential issues
                    if overlay_info['width'] % 2 != 0 or overlay_info['height'] % 2 != 0:
                        st.warning("⚠️ Odd dimensions detected. Converting for mobile compatibility...")
                        st.session_state.overlay_path = convert_to_compatible_format(st.session_state.overlay_path)
                        overlay_info = validate_video_file(st.session_state.overlay_path)
                    
                    # Load the clip
                    st.session_state.overlay_clip = VideoFileClip(
                        st.session_state.overlay_path, 
                        audio=False,
                        fps_source='fps'
                    )
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    
                    st.success(f"✅ Overlay: {overlay_file.name}")
                    
                    # Show video info
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.metric("Resolution", f"{overlay_info['width']}×{overlay_info['height']}")
                        st.caption("Portrait" if overlay_info['is_portrait'] else "Landscape")
                    with col_info2:
                        st.metric("Duration", f"{overlay_info['duration']:.1f}s")
                        st.caption(f"FPS: {overlay_info['fps']:.1f}")
                    
                    # Show preview
                    preview_img = show_single_frame_preview(st.session_state.overlay_path)
                    if preview_img:
                        st.image(preview_img, caption="Overlay preview", use_column_width=True)
                        
                else:
                    st.error("❌ Could not load video file. Try converting to MP4 format.")
                    
            except Exception as e:
                st.error(f"❌ Error loading overlay: {str(e)}")
                # Try conversion as fallback
                st.info("Attempting automatic conversion...")
                try:
                    st.session_state.overlay_path = convert_to_compatible_format(st.session_state.overlay_path)
                    st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    st.success("✅ Video converted and loaded successfully")
                except:
                    st.error("❌ Failed to process video file")

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    # Single slider for audio trim
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
    st.info(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s total)")

if st.session_state.overlay_duration > 0:
    # Single slider for overlay trim
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
    st.info(f"🎬 Overlay: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s total)")

# ---------- ENHANCED PROCESS FUNCTION ----------
def process_video_mobile_compatible():
    """Combine audio and video with mobile compatibility"""
    try:
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 30)
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration', 30)
        overlay_end = overlay_start + overlay_duration_val
        
        # Extract audio
        with st.spinner("🔊 Extracting audio..."):
            if st.session_state.bg_is_video:
                audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
            else:
                audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Process overlay video
        with st.spinner("🎬 Processing overlay..."):
            # Load overlay with mobile-compatible settings
            try:
                overlay_clip = VideoFileClip(
                    st.session_state.overlay_path, 
                    audio=False,
                    fps_source='fps'
                )
            except:
                # Fallback loading method
                overlay_clip = VideoFileClip(
                    st.session_state.overlay_path,
                    audio=False,
                    fps_source='tbr'
                )
            
            # Trim overlay
            overlay = overlay_clip.subclip(overlay_start, overlay_end)
            
            # Match durations
            if overlay.duration < final_audio_duration:
                loops_needed = int(final_audio_duration / overlay.duration) + 1
                overlay_loops = [overlay] * loops_needed
                overlay = concatenate_videoclips(overlay_loops)
                overlay = overlay.subclip(0, final_audio_duration)
            elif overlay.duration > final_audio_duration:
                overlay = overlay.subclip(0, final_audio_duration)
            
            # Ensure the overlay has audio attribute
            if not hasattr(overlay, 'audio') or overlay.audio is None:
                # Add silent audio track
                silent_array = np.zeros((int(overlay.duration * 44100), 2), dtype=np.float32)
                silent_audio = AudioArrayClip(silent_array, fps=44100)
                overlay = overlay.set_audio(silent_audio)
            
            # Combine with audio
            final_video = overlay.set_audio(audio_clip)
        
        # Save video with mobile optimization
        with st.spinner("💾 Saving video (mobile optimized)..."):
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Get dimensions
            width, height = overlay.size
            
            # Mobile-friendly encoding
            final_video.write_videofile(
                output_path,
                fps=min(30, overlay.fps),  # Cap at 30fps for mobile
                codec="libx264",
                audio_codec="aac",
                bitrate="4M",  # Optimized for mobile
                preset='fast',
                ffmpeg_params=[
                    '-movflags', '+faststart',  # Streaming optimization
                    '-pix_fmt', 'yuv420p',      # Maximum compatibility
                    '-profile:v', 'baseline',   # Mobile profile
                    '-level', '3.0',
                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2'  # Even dimensions
                ],
                verbose=False,
                logger=None,
                threads=4,
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        final_video.close()
        if 'overlay_clip' in locals():
            overlay_clip.close()
        
        return output_path, final_audio_duration, width, height
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
        import traceback
        with st.expander("🔍 Error details"):
            st.code(traceback.format_exc())
        
        # Try alternative method if first fails
        st.info("🔄 Trying alternative processing method...")
        try:
            return process_video_simple()
        except:
            return None, 0, 0, 0

def process_video_simple():
    """Simpler processing method as fallback"""
    try:
        # Simple FFMPEG command as fallback
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 30)
        
        cmd = [
            'ffmpeg',
            '-ss', str(audio_start),
            '-t', str(audio_duration_val),
            '-i', st.session_state.bg_path,
            '-i', st.session_state.overlay_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-map', '0:a:0',
            '-map', '1:v:0',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-y', output_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Get video info
        clip = VideoFileClip(output_path, audio=False)
        duration = clip.duration
        width, height = clip.size
        clip.close()
        
        return output_path, duration, width, height
        
    except Exception as e:
        st.error(f"❌ Fallback processing failed: {str(e)}")
        return None, 0, 0, 0

# ---------- CREATE BUTTON ----------
st.divider()

# Check if both files are uploaded
files_ready = st.session_state.bg_path and st.session_state.overlay_path

if st.button("🚀 Create Final Video", 
             type="primary", 
             disabled=not files_ready,
             use_container_width=True,
             help="Click to process and create your video"):
    
    if not files_ready:
        st.warning("⚠️ Please upload both background and overlay files first")
        st.stop()
    
    # Add processing option
    processing_method = st.radio(
        "Processing method:",
        ["Mobile Optimized (Recommended)", "Simple Processing"],
        horizontal=True,
        index=0
    )
    
    # Process video
    if processing_method == "Mobile Optimized (Recommended)":
        output_path, duration, width, height = process_video_mobile_compatible()
    else:
        output_path, duration, width, height = process_video_simple()
    
    if output_path and os.path.exists(output_path):
        st.success("✅ Video created successfully!")
        
        # Show video
        st.subheader("📺 Your Video Preview")
        display_video_with_fallback(output_path)
        
        # Show detailed info
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Size", f"{file_size:.1f}MB")
        with col4:
            st.metric("Aspect", f"{width/height:.2f}" if height > 0 else "N/A")
        
        # Download button
        st.divider()
        with open(output_path, "rb") as f:
            video_bytes = f.read()
            b64 = base64.b64encode(video_bytes).decode()
            href = f'<a href="data:video/mp4;base64,{b64}" download="mobile_video_{width}x{height}.mp4" style="text-decoration: none;">'
            
            col_dl1, col_dl2, col_dl3 = st.columns([1,2,1])
            with col_dl2:
                st.markdown(f"""
                <div style="text-align: center;">
                    {href}
                    <button style="background-color: #4CAF50; color: white; padding: 14px 40px; 
                    text-align: center; text-decoration: none; display: inline-block; 
                    font-size: 18px; margin: 4px 2px; cursor: pointer; border-radius: 8px;
                    border: none; width: 100%;">
                    📥 Download Video ({file_size:.1f}MB)
                    </button>
                    </a>
                </div>
                """, unsafe_allow_html=True)
        
        # Cleanup temp files
        with st.spinner("🧹 Cleaning up temporary files..."):
            try:
                temp_files = [
                    st.session_state.bg_path,
                    st.session_state.overlay_path,
                    output_path
                ]
                for temp_file in temp_files:
                    if temp_file and os.path.exists(temp_file):
                        os.unlink(temp_file)
            except:
                pass
        
        # Clear session
        for key in ['bg_path', 'overlay_path', 'bg_clip', 'overlay_clip']:
            if key in st.session_state:
                st.session_state[key] = None
        
        gc.collect()
        st.balloons()
    else:
        st.error("❌ Failed to create video. Please try different files or settings.")

# ---------- TROUBLESHOOTING GUIDE ----------
with st.expander("🔧 Troubleshooting Guide", expanded=False):
    st.markdown("""
    ### Common Issues & Solutions:
    
    **1. Video doesn't show overlay on mobile:**
    - Ensure video is MP4 format with H.264 codec
    - Use even dimensions (e.g., 1920x1080, not 1921x1080)
    - Try "Mobile Optimized" processing
    
    **2. Audio/Video sync issues:**
    - Use shorter clips (under 5 minutes)
    - Avoid Variable Frame Rate (VFR) videos
    - Convert to constant frame rate (30fps recommended)
    
    **3. Video won't play on specific devices:**
    - iPhone/Safari: Use .mp4 with AAC audio
    - Android: Most formats work, MP4 is safest
    - Older devices: Use lower resolution (720p)
    
    **4. File size too large:**
    - Shorter duration reduces size
    - Lower resolution videos are smaller
    - Consider compressing source videos first
    
    **5. Processing fails:**
    - Try smaller files (<500MB)
    - Convert to MP4 before uploading
    - Use Simple Processing method
    """)

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Mobile-Friendly Video Maker
    
    **What this does:**
    1. Takes audio from background file
    2. Takes video from overlay file
    3. Trims both to your desired length
    4. Combines them with mobile optimization
    5. Outputs MP4 with maximum device compatibility
    
    **Best Practices:**
    - **Background:** MP3 or MP4 files work best
    - **Overlay:** MP4 with H.264 codec recommended
    - **Duration:** Keep under 10 minutes for best results
    - **Resolution:** Even dimensions (e.g., 1080x1920, not 1081x1920)
    
    **Processing Options:**
    - **Mobile Optimized:** Best for sharing on phones/tablets
    - **Simple Processing:** Faster, but may have compatibility issues
    
    **Output Features:**
    - No resizing (keeps original dimensions)
    - Mobile-optimized encoding
    - Fast-start for instant playback
    - Maximum device compatibility
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("🎥 Mobile Video Maker • No Resizing • Maximum Compatibility • Version 2.1")
st.caption("For best results, use MP4 files with standard frame rates (24/30fps)")
