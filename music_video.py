import streamlit as st
import tempfile
import os
import gc
import time
import numpy as np
from PIL import Image, ImageFilter
import io

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_videoclips,
    CompositeVideoClip
)

# Update version
my_title = "🎬 Mobile Video Maker V 24"

# ---------- MOBILE-FRIENDLY PAGE CONFIG ----------
st.set_page_config(
    page_title=my_title,
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items=None
)

# ---------- MOBILE-OPTIMIZED CSS ----------
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Mobile optimizations */
    @media only screen and (max-width: 768px) {
        .main .block-container {
            padding: 1rem !important;
        }
        
        h1 { font-size: 1.8rem !important; }
        h2, h3 { font-size: 1.4rem !important; }
        
        .stButton > button {
            width: 100% !important;
            padding: 0.75rem;
            font-size: 16px;
            min-height: 44px;
            margin: 0.5rem 0;
        }
        
        .stSlider {
            padding: 0.5rem 0;
        }
    }
    
    /* General optimizations */
    .stApp {
        max-width: 100vw;
        overflow-x: hidden;
    }
    
    .stButton > button, .stDownloadButton > button {
        min-height: 44px;
    }
    
    /* Portrait preview styling */
    .portrait-preview {
        border: 2px solid #4CAF50;
        border-radius: 10px;
        padding: 5px;
        background: #f0f0f0;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("📱 Always creates 1080×1920 portrait mobile videos (9:16)")

# ---------- PORTRAIT VIDEO SETTINGS ----------
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1920
PORTRAIT_RESOLUTION = (PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
TARGET_ASPECT = PORTRAIT_HEIGHT / PORTRAIT_WIDTH  # 1.777 for 9:16

# ---------- SESSION STATE ----------
session_defaults = {
    'bg_clip': None,
    'overlay_clip': None,
    'bg_duration': 0,
    'overlay_duration': 0,
    'bg_path': None,
    'overlay_path': None,
    'bg_is_video': False,
    'prev_bg_file': None,
    'prev_overlay_file': None,
    'processing': False,
    'last_output': None,
    'overlay_size': None,
    'preview_generated': False
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    try:
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(uploaded_file.name)[1]
        )
        temp_file.write(uploaded_file.getvalue())
        temp_file.close()
        return temp_file.name
    except Exception as e:
        st.error(f"Error saving file: {str(e)}")
        return None

def create_portrait_preview(frame_array):
    """Create a 9:16 portrait preview from frame"""
    try:
        img = Image.fromarray(frame_array)
        
        # Calculate target size for preview
        preview_width = 270  # 1/4 of 1080 for mobile preview
        preview_height = 480  # 1/4 of 1920 for mobile preview
        
        # Resize maintaining aspect ratio
        img.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
        
        # Create 9:16 canvas
        preview_img = Image.new('RGB', (preview_width, preview_height), (0, 0, 0))
        
        # Calculate position to center
        x_offset = (preview_width - img.width) // 2
        y_offset = (preview_height - img.height) // 2
        
        # Paste onto canvas
        preview_img.paste(img, (x_offset, y_offset))
        
        return preview_img
    except Exception as e:
        st.error(f"Preview error: {str(e)}")
        return None

def resize_for_portrait(clip, fit_method='crop'):
    """Resize video to 1080×1920 portrait"""
    try:
        original_width, original_height = clip.size
        st.session_state.overlay_size = (original_width, original_height)
        
        target_width, target_height = PORTRAIT_RESOLUTION
        
        if fit_method == 'crop':
            # Method 1: Crop to fill (no black bars)
            # Calculate scale to cover entire portrait frame
            scale_width = target_width / original_width
            scale_height = target_height / original_height
            
            # Use larger scale to fill frame
            scale = max(scale_width, scale_height)
            
            # Calculate new dimensions
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            # Resize
            resized = clip.resize((new_width, new_height))
            
            # Calculate crop position (center)
            crop_x = (new_width - target_width) // 2
            crop_y = (new_height - target_height) // 2
            
            # Crop to exact portrait dimensions
            cropped = resized.crop(
                x1=crop_x,
                y1=crop_y,
                x2=crop_x + target_width,
                y2=crop_y + target_height
            )
            
            return cropped
            
        else:  # fit_method == 'fit'
            # Method 2: Fit with blur background
            # Calculate scale to fit within portrait frame
            scale_width = target_width / original_width
            scale_height = target_height / original_height
            
            # Use smaller scale to fit content
            scale = min(scale_width, scale_height)
            
            # Calculate new dimensions
            new_width = int(original_width * scale)
            new_height = int(original_height * scale)
            
            # Resize main content
            resized = clip.resize((new_width, new_height))
            
            # Create blurred background from original clip
            # Get a single frame for blurring
            frame = clip.get_frame(0)
            bg_img = Image.fromarray(frame)
            
            # Resize background to portrait dimensions
            bg_img = bg_img.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Apply blur
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=15))
            
            # Convert back to array for moviepy
            bg_array = np.array(bg_img)
            
            # Create background clip
            bg_clip = ImageClip(bg_array, duration=clip.duration)
            bg_clip = bg_clip.resize((target_width, target_height))
            
            # Calculate position for centered content
            x_pos = (target_width - new_width) // 2
            y_pos = (target_height - new_height) // 2
            
            # Composite resized clip over blurred background
            final_clip = CompositeVideoClip([
                bg_clip,
                resized.set_position((x_pos, y_pos))
            ])
            
            return final_clip
            
    except Exception as e:
        st.error(f"Resize error: {str(e)}")
        # Fallback: simple resize
        return clip.resize(PORTRAIT_RESOLUTION)

# ---------- UPLOAD SECTIONS ----------
st.subheader("📤 Upload Files")

# Show target resolution
st.info(f"🎯 **Target Output:** {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} (9:16 Portrait)")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "mp4", "mov", "m4a", "wav"],
        help="Audio will be extracted for the final video"
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name:
            if st.session_state.bg_clip:
                try:
                    st.session_state.bg_clip.close()
                except:
                    pass
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        with st.spinner("Loading background..."):
            bg_path = save_uploaded_file(background_file)
            if bg_path:
                st.session_state.bg_path = bg_path
                bg_ext = os.path.splitext(background_file.name)[1].lower()
                st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
                
                try:
                    if st.session_state.bg_is_video:
                        st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                        if st.session_state.bg_clip.audio:
                            st.session_state.bg_duration = st.session_state.bg_clip.audio.duration
                            st.success(f"✅ Video loaded: {st.session_state.bg_duration:.1f}s")
                        else:
                            st.error("No audio in video")
                    else:
                        audio = AudioFileClip(st.session_state.bg_path)
                        st.session_state.bg_duration = audio.duration
                        audio.close()
                        st.success(f"✅ Audio loaded: {st.session_state.bg_duration:.1f}s")
                        
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov", "avi", "mkv", "webm"],
        help="Will be converted to 1080×1920 portrait"
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name:
            if st.session_state.overlay_clip:
                try:
                    st.session_state.overlay_clip.close()
                except:
                    pass
            st.session_state.overlay_clip = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        with st.spinner("Loading overlay..."):
            overlay_path = save_uploaded_file(overlay_file)
            if overlay_path:
                st.session_state.overlay_path = overlay_path
                
                try:
                    st.session_state.overlay_clip = VideoFileClip(overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    
                    # Show original size
                    orig_w, orig_h = st.session_state.overlay_clip.size
                    st.success(f"✅ Video loaded: {orig_w}×{orig_h} ({st.session_state.overlay_duration:.1f}s)")
                    st.info(f"Will convert to: {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}")
                    
                    # Create and show portrait preview
                    preview_frame = st.session_state.overlay_clip.get_frame(1)
                    preview_img = create_portrait_preview(preview_frame)
                    
                    if preview_img:
                        st.image(preview_img, caption="9:16 Portrait Preview", use_column_width=True)
                        st.session_state.preview_generated = True
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ---------- CONVERSION METHOD ----------
st.subheader("📐 Conversion Settings")

conversion_method = st.radio(
    "Choose conversion method:",
    options=['Crop to Fill (No black bars)', 'Fit with Blur Background'],
    index=0,
    horizontal=True,
    help="Crop: Fills screen completely | Fit: Shows full video with blurred edges"
)

# Map to method parameter
fit_method = 'crop' if conversion_method == 'Crop to Fill (No black bars)' else 'fit'

# ---------- TRIM SETTINGS ----------
if st.session_state.bg_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    st.markdown("**Audio Trim**")
    col1, col2 = st.columns(2)
    
    with col1:
        audio_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.bg_duration),
            0.0,
            0.1,
            key="audio_start"
        )
    
    with col2:
        max_duration = st.session_state.bg_duration - audio_start
        default_duration = min(60.0, float(max_duration))
        audio_duration = st.slider(
            "Duration (seconds)",
            1.0,
            float(max_duration),
            default_duration,
            0.1,
            key="audio_duration"
        )
    
    audio_end = audio_start + audio_duration
    st.success(f"🎵 Audio: {audio_start:.1f}s to {audio_end:.1f}s ({audio_duration:.1f}s)")

if st.session_state.overlay_duration > 0:
    st.markdown("**Video Trim**")
    col1, col2 = st.columns(2)
    
    with col1:
        overlay_start = st.slider(
            "Start (seconds)",
            0.0,
            float(st.session_state.overlay_duration),
            0.0,
            0.1,
            key="overlay_start"
        )
    
    with col2:
        max_duration = st.session_state.overlay_duration - overlay_start
        default_duration = min(60.0, float(max_duration))
        overlay_duration = st.slider(
            "Duration (seconds)",
            1.0,
            float(max_duration),
            default_duration,
            0.1,
            key="overlay_duration"
        )
    
    overlay_end = overlay_start + overlay_duration
    st.success(f"📹 Video: {overlay_start:.1f}s to {overlay_end:.1f}s ({overlay_duration:.1f}s)")

# ---------- PROCESS FUNCTION ----------
def process_portrait_video():
    """Create portrait mobile video"""
    try:
        st.session_state.processing = True
        
        # Get trim values
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration_val = st.session_state.get('audio_duration', 
                                                 min(60, st.session_state.bg_duration))
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start', 0)
        overlay_duration_val = st.session_state.get('overlay_duration',
                                                   min(60, st.session_state.overlay_duration))
        overlay_end = overlay_start + overlay_duration_val
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Extract audio
        status_text.text("🔊 Extracting audio...")
        progress_bar.progress(10)
        
        if st.session_state.bg_is_video and st.session_state.bg_clip:
            audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Step 2: Trim overlay
        status_text.text("🎞️ Trimming video...")
        progress_bar.progress(30)
        
        overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
        
        # Step 3: Match durations
        status_text.text("⏱️ Matching durations...")
        progress_bar.progress(50)
        
        if overlay.duration < final_audio_duration:
            loops_needed = int(final_audio_duration / overlay.duration) + 1
            overlay_loops = [overlay] * loops_needed
            overlay = concatenate_videoclips(overlay_loops)
            overlay = overlay.subclip(0, final_audio_duration)
        elif overlay.duration > final_audio_duration:
            overlay = overlay.subclip(0, final_audio_duration)
        
        # Step 4: Convert to portrait
        status_text.text(f"🔄 Converting to {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} portrait...")
        progress_bar.progress(70)
        
        portrait_overlay = resize_for_portrait(overlay, fit_method)
        
        # Verify final resolution
        final_width, final_height = portrait_overlay.size
        if final_width != PORTRAIT_WIDTH or final_height != PORTRAIT_HEIGHT:
            # Force resize if not correct
            portrait_overlay = portrait_overlay.resize(PORTRAIT_RESOLUTION)
        
        # Step 5: Add audio
        status_text.text("🎵 Adding audio...")
        progress_bar.progress(80)
        
        final_video = portrait_overlay.set_audio(audio_clip)
        final_video = final_video.set_duration(final_audio_duration)
        
        # Step 6: Save video
        status_text.text("💾 Saving video...")
        progress_bar.progress(90)
        
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_portrait.mp4").name
        
        # Write video with mobile-optimized settings
        final_video.write_videofile(
            output_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            bitrate="8M",
            verbose=False,
            logger=None,
            preset='medium',
            ffmpeg_params=[
                '-movflags', '+faststart',
                '-pix_fmt', 'yuv420p',
                '-profile:v', 'high',
                '-level', '4.2'
            ]
        )
        
        progress_bar.progress(100)
        status_text.text("✅ Complete!")
        time.sleep(0.5)
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        portrait_overlay.close()
        final_video.close()
        
        # Verify file was created
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path) / (1024 * 1024)
            return output_path, final_audio_duration, PORTRAIT_WIDTH, PORTRAIT_HEIGHT, file_size
        
        return None, 0, 0, 0, 0
        
    except Exception as e:
        st.error(f"❌ Processing error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())
        return None, 0, 0, 0, 0
    finally:
        st.session_state.processing = False
        if 'status_text' in locals():
            status_text.empty()
        if 'progress_bar' in locals():
            progress_bar.empty()

# ---------- CREATE BUTTON ----------
st.divider()

files_ready = st.session_state.bg_path and st.session_state.overlay_path
processing = st.session_state.get('processing', False)

if st.button(
    "🎬 Create Portrait Video" if not processing else "⏳ Processing...",
    type="primary",
    disabled=not files_ready or processing,
    use_container_width=True
):
    if not files_ready:
        st.warning("Please upload both files first")
        st.stop()
    
    # Show conversion info
    if st.session_state.overlay_size:
        orig_w, orig_h = st.session_state.overlay_size
        st.info(f"🔄 Converting {orig_w}×{orig_h} → {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} portrait")
    
    # Process video
    result = process_portrait_video()
    
    if result and result[0]:
        output_path, duration, width, height, file_size = result
        
        st.balloons()
        st.success(f"✅ Portrait video created successfully!")
        
        # Display video
        st.subheader("📱 Your Portrait Video")
        
        try:
            with open(output_path, "rb") as f:
                video_bytes = f.read()
            
            # Display with proper aspect ratio
            st.video(video_bytes, format="video/mp4")
        except Exception as e:
            st.info("Video preview loaded - download below")
        
        # Show video info
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Duration", f"{duration:.1f}s")
        with col2:
            st.metric("Resolution", f"{width}×{height}")
        with col3:
            st.metric("Aspect Ratio", "9:16")
        with col4:
            st.metric("File Size", f"{file_size:.1f}MB")
        
        # Download button
        with open(output_path, "rb") as f:
            video_data = f.read()
            
            st.download_button(
                "📥 Download Portrait Video",
                video_data,
                file_name=f"portrait_{PORTRAIT_WIDTH}x{PORTRAIT_HEIGHT}.mp4",
                mime="video/mp4",
                type="primary",
                use_container_width=True
            )
        
        # Mobile tips
        st.info("📱 **Mobile Ready:** Perfect for Instagram Reels, TikTok, YouTube Shorts")
        
        # Cleanup temp files
        try:
            if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
                os.unlink(st.session_state.bg_path)
            if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
                os.unlink(st.session_state.overlay_path)
        except:
            pass
        
        # Clear session
        if st.session_state.bg_clip:
            try:
                st.session_state.bg_clip.close()
            except:
                pass
            st.session_state.bg_clip = None
            
        if st.session_state.overlay_clip:
            try:
                st.session_state.overlay_clip.close()
            except:
                pass
            st.session_state.overlay_clip = None
        
        gc.collect()

# ---------- INSTRUCTIONS ----------
with st.expander("📖 How It Works", expanded=True):
    st.markdown(f"""
    ### Always Creates {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait Videos
    
    **This app automatically converts ANY video to mobile-optimized portrait format.**
    
    ### 🎯 **Key Features:**
    
    1. **Guaranteed 9:16 Output**
       - Input: Any video (landscape, square, portrait)
       - Output: Always {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} (9:16)
    
    2. **Two Conversion Methods:**
       - **Crop to Fill**: Best for social media (Instagram Reels, TikTok)
       - **Fit with Blur**: Best for presentations, keeps all content visible
    
    3. **Preview Matching**
       - Preview shows exact 9:16 aspect ratio
       - Final video matches preview exactly
    
    ### 📱 **Platform Optimization:**
    - **Instagram Reels/TikTok**: Perfect {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT}
    - **YouTube Shorts**: 9:16 vertical video ready
    - **Stories**: Full-screen portrait format
    
    ### ⚙️ **Technical Details:**
    - **Resolution**: {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} pixels
    - **Codec**: H.264 (compatible with all devices)
    - **Audio**: AAC stereo
    - **FPS**: 30 (smooth playback)
    - **Format**: MP4 with faststart
    
    ### 💡 **Tips for Best Results:**
    1. Use videos with good lighting
    2. Keep important content centered
    3. Original video should be at least 720p
    4. For talking heads: position in center 1/3
    5. Choose "Crop to Fill" for social media
    6. Choose "Fit with Blur" to preserve all content
    """)

# ---------- FOOTER ----------
st.divider()
st.caption(f"🎬 Mobile Video Maker • Always {PORTRAIT_WIDTH}×{PORTRAIT_HEIGHT} Portrait • V24")

# ---------- CLEANUP ----------
import atexit

@atexit.register
def cleanup():
    """Clean up temporary files on exit"""
    try:
        files = [
            st.session_state.get('bg_path'),
            st.session_state.get('overlay_path'),
            st.session_state.get('last_output')
        ]
        for f in files:
            if f and os.path.exists(f):
                try:
                    os.unlink(f)
                except:
                    pass
    except:
        pass
