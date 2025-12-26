import streamlit as st
import tempfile
import os
import subprocess
from PIL import Image
import shutil

# ---------- CONFIG ----------
VERSION = "3.4.0"
SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
st.set_page_config(page_title="Mobile Video Maker", layout="centered")

# ---------- SESSION STATE INITIALIZATION ----------
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.audio_range = [0, 15]
    st.session_state.video_range = [0, 15]
    st.session_state.audio_duration = 0
    st.session_state.video_duration = 0
    st.session_state.audio_temp_path = ""
    st.session_state.overlay_temp_path = ""
    st.session_state.media_type = None

# ---------- UTILITIES ----------
class MediaProcessor:
    @staticmethod
    def get_duration(file_path):
        """Get duration of any media file"""
        try:
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                   '-of', 'default=noprint_wrappers=1:nokey=1', file_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip())
            return max(duration, 1.0)  # Ensure at least 1 second
        except Exception as e:
            st.warning(f"Could not determine duration, using default: {str(e)[:100]}")
            return 30.0
    
    @staticmethod
    def create_preview(file_path, start, end, output_path, is_video=True):
        """Create preview video of selected range"""
        try:
            duration = min(end - start, 10)
            if duration <= 0:
                duration = 1.0
            
            cmd = ['ffmpeg', '-ss', str(start), '-i', file_path, '-t', str(duration)]
            
            if is_video:
                cmd.extend(['-vf', 'scale=640:-1', '-c:v', 'libx264', '-c:a', 'aac', '-b:a', '128k'])
            else:
                cmd.extend([
                    '-filter_complex', 
                    '[0:a]showwaves=s=640x240:mode=line:colors=white[v]', 
                    '-map', '[v]',
                    '-frames:v', '1'  # Single frame for audio visualization
                ])
            
            cmd.extend(['-y', output_path])
            subprocess.run(cmd, capture_output=True, check=True, timeout=30)
            return True
        except subprocess.TimeoutExpired:
            st.error("Preview generation timed out")
            return False
        except Exception as e:
            st.warning(f"Preview generation failed: {str(e)[:100]}")
            return False
    
    @staticmethod
    def create_thumbnail(file_path, time_point, output_path):
        """Create thumbnail at specific time"""
        try:
            cmd = [
                'ffmpeg', '-ss', str(max(time_point, 0.1)), '-i', file_path,
                '-vframes', '1', '-vf', 'scale=320:-1', '-y', output_path
            ]
            subprocess.run(cmd, capture_output=True, check=True, timeout=10)
            return True
        except Exception:
            return False

# ---------- UI COMPONENTS ----------
def render_range_selector(file, title, media_type, is_video=True):
    """Render range selector with preview for any media"""
    if not file: 
        return None, None, None
    
    with st.expander(f"✂️ {title}", expanded=True):
        temp_dir = tempfile.mkdtemp()
        file_ext = os.path.splitext(file.name)[1]
        if not file_ext:
            file_ext = ".mp4" if is_video else ".mp3"
        
        temp_path = os.path.join(temp_dir, f"temp{file_ext}")
        
        # Save file to temp location
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        
        # Store temp path in session state
        if media_type == "audio":
            st.session_state.audio_temp_path = temp_path
        else:
            st.session_state.overlay_temp_path = temp_path
        
        # Get duration
        try:
            duration = MediaProcessor.get_duration(temp_path)
            if media_type == "audio":
                st.session_state.audio_duration = duration
            else:
                st.session_state.video_duration = duration
        except Exception as e:
            st.error(f"Could not read {media_type} duration: {str(e)[:100]}")
            duration = 30.0
        
        st.info(f"Total length: **{duration:.1f} seconds**")
        
        # Range slider
        range_key = f"{media_type}_range"
        current_range = st.session_state.get(range_key, [0.0, min(duration, 15.0)])
        
        range_vals = st.slider(
            "Select start and end points",
            0.0,
            float(duration),
            value=(float(current_range[0]), float(min(duration, current_range[1]))),
            step=0.1,
            format="%.1f s",
            key=f"{media_type}_range_slider"
        )
        
        st.session_state[range_key] = list(range_vals)
        start, end = range_vals
        selected_duration = end - start
        
        # Display duration info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Start", f"{start:.1f}s")
        with col2:
            st.metric("End", f"{end:.1f}s")
        with col3:
            st.metric("Duration", f"{selected_duration:.1f}s")
        
        # Preview section
        st.markdown("---")
        st.subheader("🔍 Preview")
        
        if is_video and st.button("📸 Generate Preview", key=f"preview_{media_type}"):
            with st.spinner("Creating preview..."):
                # Create thumbnails for start and end
                col_start, col_end = st.columns(2)
                
                with col_start:
                    thumb_start = os.path.join(temp_dir, "thumb_start.jpg")
                    if MediaProcessor.create_thumbnail(temp_path, start, thumb_start):
                        st.image(thumb_start, caption=f"Start: {start:.1f}s", use_container_width=True)
                
                with col_end:
                    thumb_end = os.path.join(temp_dir, "thumb_end.jpg")
                    if MediaProcessor.create_thumbnail(temp_path, end - 0.1, thumb_end):
                        st.image(thumb_end, caption=f"End: {end:.1f}s", use_container_width=True)
                
                # Create video preview
                preview_path = os.path.join(temp_dir, f"{media_type}_preview.mp4")
                if MediaProcessor.create_preview(temp_path, start, end, preview_path, is_video):
                    if os.path.exists(preview_path):
                        st.video(preview_path, format="video/mp4")
                        st.success("Preview generated!")
                else:
                    st.warning("Could not generate video preview")
        
        elif not is_video and st.button("🎧 Generate Audio Preview", key=f"audio_preview_{media_type}"):
            with st.spinner("Creating audio preview..."):
                preview_path = os.path.join(temp_dir, f"{media_type}_preview.mp4")
                if MediaProcessor.create_preview(temp_path, start, end, preview_path, is_video=False):
                    if os.path.exists(preview_path):
                        st.video(preview_path, format="video/mp4")
                        st.success("Audio preview generated!")
                else:
                    st.warning("Could not generate audio preview")
        
        # Don't clean up temp dir yet - we need the file for processing
        return start, end, selected_duration, temp_dir

def process_image_overlay(image_path, output_path, audio_duration, temp_dir):
    """Process image overlay with background audio"""
    try:
        # Resize image
        img = Image.open(image_path)
        img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), Image.Resampling.LANCZOS)
        resized_path = os.path.join(temp_dir, "resized_image.jpg")
        img.save(resized_path, "JPEG", quality=95)
        
        cmd = [
            'ffmpeg',
            '-loop', '1',
            '-i', resized_path,
            '-i', st.session_state.audio_temp_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-vf', f'scale={SCREEN_WIDTH}:{SCREEN_HEIGHT},format=yuv420p',
            '-shortest',
            '-t', str(audio_duration),
            '-y', output_path
        ]
        return cmd
    except Exception as e:
        st.error(f"Image processing failed: {str(e)}")
        return None

def process_video_overlay(video_path, output_path, audio_start, audio_duration, video_start, video_duration, temp_dir):
    """Process video overlay with background audio"""
    try:
        final_duration = min(audio_duration, video_duration)
        
        # Trim video to selected range
        trimmed_video = os.path.join(temp_dir, "trimmed_video.mp4")
        cmd_trim = [
            'ffmpeg',
            '-ss', str(video_start),
            '-i', video_path,
            '-t', str(video_duration),
            '-c', 'copy',
            '-y', trimmed_video
        ]
        
        result = subprocess.run(cmd_trim, capture_output=True, text=True)
        if result.returncode != 0:
            st.warning("Could not trim video, using original")
            trimmed_video = video_path
            final_duration = min(audio_duration, st.session_state.video_duration)
        
        # Loop video if shorter than needed
        if video_duration < final_duration:
            loop_count = int(final_duration // video_duration) + 1
            concat_list = os.path.join(temp_dir, "concat_list.txt")
            
            with open(concat_list, "w") as f:
                for _ in range(loop_count):
                    f.write(f"file '{trimmed_video}'\n")
            
            looped_video = os.path.join(temp_dir, "looped.mp4")
            cmd_loop = [
                'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_list,
                '-c', 'copy', '-t', str(final_duration), '-y', looped_video
            ]
            subprocess.run(cmd_loop, capture_output=True, text=True)
            trimmed_video = looped_video
        
        # Create final video with cropping for mobile aspect
        cmd = [
            'ffmpeg',
            '-i', trimmed_video,
            '-ss', str(audio_start),
            '-i', st.session_state.audio_temp_path,
            '-filter_complex', 
            f'[0:v]crop=ih*9/16:ih,scale={SCREEN_WIDTH}:{SCREEN_HEIGHT},format=yuv420p[v]',
            '-map', '[v]',
            '-map', '1:a',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',
            '-t', str(final_duration),
            '-y', output_path
        ]
        return cmd
    except Exception as e:
        st.error(f"Video processing failed: {str(e)}")
        return None

# ---------- MAIN APP ----------
def main():
    st.title(f"📱 Mobile Video Maker v{VERSION}")
    st.markdown("Create vertical videos (1080×1920) for mobile platforms")
    
    # File uploaders
    col1, col2 = st.columns(2)
    with col1:
        audio_file = st.file_uploader(
            "🎵 Background Audio", 
            type=["mp3", "wav", "m4a", "mp4", "mov"],
            help="Upload audio or video file for background music/sound"
        )
    
    with col2:
        overlay_file = st.file_uploader(
            "🎬 Overlay Content", 
            type=["mp4", "mov", "png", "jpg", "jpeg"],
            help="Upload video or image to display on screen"
        )
    
    audio_data = None
    video_data = None
    
    # Process audio if uploaded
    if audio_file:
        with st.container():
            st.subheader("🎵 Audio Settings")
            audio_data = render_range_selector(audio_file, "Trim Audio", "audio", is_video=False)
    
    # Process overlay if uploaded
    if overlay_file:
        with st.container():
            st.subheader("🎬 Overlay Settings")
            is_image = overlay_file.type.startswith('image') or overlay_file.name.lower().endswith(('.png', '.jpg', '.jpeg'))
            video_data = render_range_selector(overlay_file, "Trim Overlay", "video", is_video=not is_image)
    
    # Create button
    st.markdown("---")
    create_disabled = not (audio_file and overlay_file)
    
    if create_disabled:
        st.info("👆 Please upload both audio and overlay files to continue")
    
    if st.button("🎬 Create Mobile Video", 
                 type="primary", 
                 use_container_width=True,
                 disabled=create_disabled):
        
        with st.spinner("🎥 Processing your mobile video..."):
            temp_dir = tempfile.mkdtemp()
            output_path = os.path.join(temp_dir, "mobile_video.mp4")
            
            try:
                # Extract data from selectors
                if audio_data:
                    audio_start, audio_end, audio_duration, _ = audio_data
                else:
                    audio_start, audio_end, audio_duration = 0, 15, 15
                
                # Determine if overlay is image
                is_image = overlay_file.type.startswith('image') or overlay_file.name.lower().endswith(('.png', '.jpg', '.jpeg'))
                
                # Build FFmpeg command based on overlay type
                if is_image:
                    cmd = process_image_overlay(
                        st.session_state.overlay_temp_path,
                        output_path,
                        audio_duration,
                        temp_dir
                    )
                else:
                    if video_data:
                        video_start, video_end, video_duration, _ = video_data
                    else:
                        video_start, video_end, video_duration = 0, 15, 15
                    
                    cmd = process_video_overlay(
                        st.session_state.overlay_temp_path,
                        output_path,
                        audio_start,
                        audio_duration,
                        video_start,
                        video_duration,
                        temp_dir
                    )
                
                if cmd is None:
                    st.error("Failed to build processing command")
                    return
                
                # Execute FFmpeg
                st.info("⚙️ Processing with FFmpeg...")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    st.error(f"❌ Processing failed!")
                    with st.expander("Error Details"):
                        st.code(result.stderr)
                    return
                
                # Verify output
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    st.error("Output file was not created")
                    return
                
                # Display success and video
                st.success("✅ Video created successfully!")
                st.balloons()
                
                # Show video
                st.subheader("📱 Your Mobile Video")
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
                with col2:
                    st.metric("File Size", f"{file_size:.1f} MB")
                with col3:
                    st.metric("Duration", f"{audio_duration:.1f}s")
                
                # Display video
                st.video(output_path, format="video/mp4")
                
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
                
            except Exception as e:
                st.error(f"❌ An error occurred: {str(e)}")
                with st.expander("Technical Details"):
                    st.exception(e)
            
            finally:
                # Cleanup
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except:
                    pass
    
    # Instructions
    with st.expander("📖 Instructions & Tips", expanded=False):
        st.markdown("""
        ### 🚀 How to Use:
        1. **Upload Background Audio** - Music, voiceover, or any audio track
        2. **Upload Overlay Content** - Video or image to display
        3. **Trim Both** using the range sliders
        4. **Preview** your selections
        5. **Create** the final vertical video
        
        ### 🎯 Features:
        - **Vertical Format**: 1080×1920 (perfect for Instagram, TikTok)
        - **Smart Cropping**: Automatically crops to 9:16 aspect ratio
        - **Range Selection**: Precise trimming for both audio and video
        - **Live Previews**: See what you're selecting before processing
        - **Video Looping**: Automatically loops video if shorter than audio
        
        ### 💡 Tips for Best Results:
        - Use **vertical videos** (9:16) for best quality
        - Keep **audio under 5 minutes** for faster processing
        - Use **MP4 format** for best compatibility
        - **Preview** your selections before final creation
        
        ### ⚠️ Troubleshooting:
        - Ensure **FFmpeg** is installed on your system
        - Check file permissions if uploads fail
        - Use supported formats (MP4, MOV, MP3, WAV, PNG, JPG)
        - For large files, processing may take a few minutes
        """)

# ---------- RUN APP ----------
if __name__ == "__main__":
    # Check for FFmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        main()
    except (subprocess.CalledProcessError, FileNotFoundError):
        st.error("""
        ❌ **FFmpeg not found!**
        
        This app requires FFmpeg to be installed on your system.
        
        **Installation instructions:**
        
        **Windows:**
        1. Download from https://ffmpeg.org/download.html
        2. Add FFmpeg to your system PATH
        
        **Mac:**
        ```bash
        brew install ffmpeg
        ```
        
        **Linux:**
        ```bash
        sudo apt update
        sudo apt install ffmpeg
        ```
        
        After installing, restart this app.
        """)
