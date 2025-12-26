import streamlit as st
import tempfile
import os
import numpy as np
from PIL import Image
from io import BytesIO
import base64

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
VERSION = "2.3.0"  # Updated version

# ---------- PAGE ----------
st.set_page_config(page_title="Fullscreen Video Maker", layout="centered")
st.title(f"📱 Fullscreen Video Maker v{VERSION}")
st.markdown("Create fullscreen videos with background audio")

# ---------- SESSION STATE ----------
if 'bg_clip' not in st.session_state:
    st.session_state.bg_clip = None
if 'overlay_clip' not in st.session_state:
    st.session_state.overlay_clip = None
if 'bg_duration' not in st.session_state:
    st.session_state.bg_duration = 0
if 'overlay_duration' not in st.session_state:
    st.session_state.overlay_duration = 0
if 'bg_preview_path' not in st.session_state:
    st.session_state.bg_preview_path = None
if 'overlay_preview_path' not in st.session_state:
    st.session_state.overlay_preview_path = None
if 'bg_audio_clip' not in st.session_state:
    st.session_state.bg_audio_clip = None
if 'bg_path' not in st.session_state:
    st.session_state.bg_path = None
if 'overlay_path' not in st.session_state:
    st.session_state.overlay_path = None
if 'bg_is_video' not in st.session_state:
    st.session_state.bg_is_video = False
if 'overlay_is_image' not in st.session_state:
    st.session_state.overlay_is_image = False

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location and return path"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

def generate_video_preview(video_path, start_time=0, end_time=None, height=200):
    """Generate preview GIF for video"""
    try:
        # Convert all parameters to appropriate types
        video_path = str(video_path)
        start_time = float(start_time)
        height = int(float(height))
        
        clip = VideoFileClip(video_path)
        
        if end_time is None or end_time > clip.duration:
            end_time = min(float(clip.duration), start_time + 3.0)
        else:
            end_time = float(end_time)
        
        # Ensure valid time range
        start_time = max(0.0, min(start_time, float(clip.duration) - 0.1))
        end_time = max(start_time + 0.1, min(end_time, float(clip.duration)))
        
        preview_clip = clip.subclip(start_time, end_time)
        
        # Ensure height is positive integer
        if height <= 0:
            height = 200
        
        # Resize with integer height, maintain aspect ratio
        preview_clip = preview_clip.resize(height=height)
        
        # Create temp file for GIF
        temp_gif = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
        temp_gif.close()
        
        # Write GIF with lower quality for speed
        preview_clip.write_gif(temp_gif.name, fps=3, program='ffmpeg')
        
        clip.close()
        preview_clip.close()
        
        return temp_gif.name
    except Exception as e:
        # Don't show error for preview - just return None
        return None

def generate_image_preview(image_path, max_size=(300, 300)):
    """Generate preview for image"""
    try:
        image_path = str(image_path)
        max_width = int(float(max_size[0]))
        max_height = int(float(max_size[1]))
        
        img = Image.open(image_path)
        
        # Ensure max dimensions are positive
        max_width = max(100, max_width)
        max_height = max(100, max_height)
        
        img.thumbnail((max_width, max_height))
        
        temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img.save(temp_img.name, format='PNG')
        temp_img.close()
        
        return temp_img.name
    except Exception as e:
        # Don't show error for preview - just return None
        return None

def display_preview(preview_path, title, is_gif=True, start_time=0, end_time=None):
    """Display preview with timing info"""
    if preview_path and os.path.exists(preview_path):
        if is_gif:
            # Read GIF and convert to base64
            with open(preview_path, 'rb') as f:
                gif_bytes = f.read()
            b64 = base64.b64encode(gif_bytes).decode()
            
            # Create HTML for GIF with timing overlay
            html = f"""
            <div style="position: relative; margin: 10px 0; border: 2px solid #ddd; border-radius: 8px; overflow: hidden;">
                <img src="data:image/gif;base64,{b64}" style="width: 100%; height: auto;">
                <div style="position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,0.7); color: white; padding: 5px; font-size: 12px; text-align: center;">
                    {title} | Start: {start_time:.1f}s | End: {end_time:.1f}s
                </div>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
        else:
            # Display image
            st.image(preview_path, caption=title, use_column_width=True)

# ---------- UPLOADS ----------
col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Music/Video",
        type=["mp3", "wav", "m4a", "aac", "mp4", "mov", "avi", "mpeg", "mkv"],
        help="Upload ANY file - only audio will be used"
    )
    
    if background_file:
        # Clear previous state if new file uploaded
        if 'prev_bg_file' not in st.session_state or st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.bg_audio_clip = None
            st.session_state.bg_preview_path = None
            st.session_state.prev_bg_file = background_file.name
        
        # Save file
        st.session_state.bg_path = save_uploaded_file(background_file)
        bg_ext = os.path.splitext(background_file.name)[1].lower()
        st.session_state.bg_is_video = background_file.type.startswith('video') or bg_ext in ['.mp4', '.mov', '.avi', '.mpeg', '.mkv']
        
        # Load the clip
        try:
            if st.session_state.bg_is_video:
                st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                st.session_state.bg_audio_clip = st.session_state.bg_clip.audio
                if st.session_state.bg_audio_clip is None:
                    st.error("❌ No audio found in video!")
                    st.stop()
            else:
                st.session_state.bg_clip = None
                st.session_state.bg_audio_clip = AudioFileClip(st.session_state.bg_path)
            
            st.session_state.bg_duration = float(st.session_state.bg_audio_clip.duration)
            
            # Generate preview if video (silently - don't show errors)
            if st.session_state.bg_is_video:
                st.session_state.bg_preview_path = generate_video_preview(
                    st.session_state.bg_path, 
                    start_time=0.0, 
                    end_time=min(3.0, st.session_state.bg_duration),
                    height=200
                )
            
            st.success(f"✅ Loaded: {background_file.name} ({st.session_state.bg_duration:.1f}s)")
            
        except Exception as e:
            st.error(f"Error loading background: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Fullscreen Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif", "webp", "bmp"],
        help="Upload image/video - will fill entire screen"
    )
    
    if overlay_file:
        # Clear previous state if new file uploaded
        if 'prev_overlay_file' not in st.session_state or st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.overlay_preview_path = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Save file
        st.session_state.overlay_path = save_uploaded_file(overlay_file)
        overlay_ext = os.path.splitext(overlay_file.name)[1].lower()
        st.session_state.overlay_is_image = overlay_file.type.startswith('image') or overlay_ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
        
        # Load the clip
        try:
            if st.session_state.overlay_is_image:
                # For images, we'll load later during processing
                st.session_state.overlay_clip = None
                st.session_state.overlay_duration = 0.0
                st.session_state.overlay_preview_path = generate_image_preview(st.session_state.overlay_path)
            else:
                st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path)
                st.session_state.overlay_duration = float(st.session_state.overlay_clip.duration)
                
                # Generate preview (silently - don't show errors)
                st.session_state.overlay_preview_path = generate_video_preview(
                    st.session_state.overlay_path,
                    start_time=0.0,
                    end_time=min(3.0, st.session_state.overlay_duration),
                    height=200
                )
            
            st.success(f"✅ Loaded: {overlay_file.name}")
            
        except Exception as e:
            st.error(f"Error loading overlay: {str(e)}")

# ---------- DURATION SELECTION ----------
if st.session_state.bg_duration > 0:
    st.subheader("🎵 Duration Selection")
    
    # Create tabs for audio and overlay settings
    audio_tab, overlay_tab = st.tabs(["🎵 Audio Settings", "🎬 Overlay Settings"])
    
    with audio_tab:
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("**Audio Duration Selector**")
            audio_start = st.slider(
                "Start Time (seconds)",
                0.0,
                float(st.session_state.bg_duration),
                0.0,
                0.1,
                key="audio_start",
                help="Select start point for audio"
            )
        
        with col_a2:
            st.markdown("**Audio Duration Range**")
            audio_end = st.slider(
                "End Time (seconds)",
                0.0,
                float(st.session_state.bg_duration),
                float(st.session_state.bg_duration),
                0.1,
                key="audio_end",
                help="Select end point for audio"
            )
        
        # Ensure end is after start
        if audio_end <= audio_start:
            audio_end = min(audio_start + 1.0, float(st.session_state.bg_duration))
            st.warning(f"End time adjusted to {audio_end:.1f} seconds")
        
        audio_duration = audio_end - audio_start
        st.info(f"**Selected audio duration: {audio_duration:.1f} seconds** (from {audio_start:.1f}s to {audio_end:.1f}s)")
    
    with overlay_tab:
        if not st.session_state.overlay_is_image and st.session_state.overlay_duration > 0:
            col_o1, col_o2 = st.columns(2)
            
            with col_o1:
                st.markdown("**Overlay Start Time**")
                overlay_start = st.slider(
                    "Start Time (seconds)",
                    0.0,
                    float(st.session_state.overlay_duration),
                    0.0,
                    0.1,
                    key="overlay_start",
                    help="Select start point for overlay video"
                )
            
            with col_o2:
                st.markdown("**Overlay End Time**")
                overlay_end = st.slider(
                    "End Time (seconds)",
                    0.0,
                    float(st.session_state.overlay_duration),
                    float(st.session_state.overlay_duration),
                    0.1,
                    key="overlay_end",
                    help="Select end point for overlay video"
                )
            
            # Ensure end is after start
            if overlay_end <= overlay_start:
                overlay_end = min(overlay_start + 1.0, float(st.session_state.overlay_duration))
                st.warning(f"End time adjusted to {overlay_end:.1f} seconds")
            
            overlay_selected_duration = overlay_end - overlay_start
            st.info(f"**Selected overlay duration: {overlay_selected_duration:.1f} seconds** (from {overlay_start:.1f}s to {overlay_end:.1f}s)")

# ---------- MOBILE SCREEN SETTINGS ----------
st.sidebar.subheader("📱 Screen Settings")
screen_option = st.sidebar.selectbox(
    "Screen Size",
    ["Instagram Reels (1080x1920)", "TikTok (1080x1920)", "YouTube Shorts (1080x1920)", 
     "Instagram Square (1080x1080)", "Custom Size"]
)

if screen_option == "Instagram Reels (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "TikTok (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "YouTube Shorts (1080x1920)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1920
elif screen_option == "Instagram Square (1080x1080)":
    SCREEN_WIDTH, SCREEN_HEIGHT = 1080, 1080
else:
    SCREEN_WIDTH = int(st.sidebar.number_input("Width", min_value=480, max_value=3840, value=1080))
    SCREEN_HEIGHT = int(st.sidebar.number_input("Height", min_value=480, max_value=3840, value=1920))

st.sidebar.info(f"Screen: {SCREEN_WIDTH} × {SCREEN_HEIGHT}")

# ---------- OVERLAY FIT OPTIONS ----------
st.sidebar.subheader("🎨 Fit Options")
fit_option = st.sidebar.radio(
    "How to fit overlay on screen",
    ["Fill Screen (Crop if needed)", "Fit Entire (Keep all content)", "Stretch to Fit"]
)

# ---------- PROCESS ----------
if st.button("🎬 Create Fullscreen Video", type="primary") and background_file and overlay_file:
    
    # Get selected durations from session state and ensure proper types
    audio_start = float(st.session_state.get('audio_start', 0))
    audio_end = float(st.session_state.get('audio_end', st.session_state.bg_duration))
    overlay_start = float(st.session_state.get('overlay_start', 0))
    overlay_end = float(st.session_state.get('overlay_end', st.session_state.overlay_duration))
    
    # Round to 2 decimal places to avoid precision issues
    audio_start = round(audio_start, 2)
    audio_end = round(audio_end, 2)
    overlay_start = round(overlay_start, 2)
    overlay_end = round(overlay_end, 2)
    
    # Ensure integer dimensions
    SCREEN_WIDTH = int(SCREEN_WIDTH)
    SCREEN_HEIGHT = int(SCREEN_HEIGHT)
    
    with st.spinner("Creating your fullscreen video..."):
        
        try:
            # ----- STEP 1: EXTRACT AND TRIM AUDIO -----
            st.info("🎵 Extracting and trimming audio...")
            
            # Create subclip for audio with explicit float conversion
            audio_clip = st.session_state.bg_audio_clip.subclip(float(audio_start), float(audio_end))
            audio_duration = float(audio_clip.duration)
            st.info(f"Audio: {audio_duration:.1f} seconds (from {audio_start:.1f}s to {audio_end:.1f}s)")
            
            # ----- STEP 2: PROCESS OVERLAY -----
            st.info("🖼️ Processing overlay for fullscreen...")
            
            if st.session_state.overlay_is_image:
                # Open image
                img = Image.open(st.session_state.overlay_path)
                img_width, img_height = img.size
                img_width, img_height = int(img_width), int(img_height)
                st.info(f"Original image: {img_width} × {img_height}")
                
                # Calculate scaling based on fit option
                screen_ratio = float(SCREEN_WIDTH) / float(SCREEN_HEIGHT)
                image_ratio = float(img_width) / float(img_height)
                
                if fit_option == "Fill Screen (Crop if needed)":
                    # Crop to fill screen completely
                    if image_ratio > screen_ratio:
                        # Image is wider than screen - crop sides
                        new_height = img_height
                        new_width = int(float(img_height) * screen_ratio)
                        left = (img_width - new_width) // 2
                        top = 0
                        right = left + new_width
                        bottom = img_height
                    else:
                        # Image is taller than screen - crop top/bottom
                        new_width = img_width
                        new_height = int(float(img_width) / screen_ratio)
                        left = 0
                        top = (img_height - new_height) // 2
                        right = img_width
                        bottom = top + new_height
                    
                    # Ensure integer coordinates
                    left, top, right, bottom = int(left), int(top), int(right), int(bottom)
                    img = img.crop((left, top, right, bottom))
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    # Fit entire image within screen (black bars)
                    if image_ratio > screen_ratio:
                        # Image is wider - fit to width
                        new_width = SCREEN_WIDTH
                        new_height = int(float(SCREEN_WIDTH) / image_ratio)
                    else:
                        # Image is taller - fit to height
                        new_height = SCREEN_HEIGHT
                        new_width = int(float(SCREEN_HEIGHT) * image_ratio)
                    
                    new_width, new_height = int(new_width), int(new_height)
                    img = img.resize((new_width, new_height), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                    
                    # Create new image with black background
                    background = Image.new('RGB', (SCREEN_WIDTH, SCREEN_HEIGHT), (0, 0, 0))
                    # Paste centered
                    paste_x = int((SCREEN_WIDTH - new_width) // 2)
                    paste_y = int((SCREEN_HEIGHT - new_height) // 2)
                    background.paste(img, (paste_x, paste_y))
                    img = background
                    
                else:  # "Stretch to Fit"
                    # Stretch image to fill screen (distorts if aspect ratio differs)
                    img = img.resize((SCREEN_WIDTH, SCREEN_HEIGHT), 
                                    Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
                
                # Save processed image
                temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                img.save(temp_img.name, "PNG", quality=95)
                temp_img_path = temp_img.name
                
                # Create image clip
                overlay = ImageClip(temp_img_path, duration=audio_duration)
                
            else:
                # VIDEO OVERLAY - Use the already loaded clip
                overlay = st.session_state.overlay_clip
                
                # Trim overlay if needed (ensure float times)
                overlay_start_float = float(overlay_start)
                overlay_end_float = float(overlay_end)
                overlay = overlay.subclip(overlay_start_float, overlay_end_float)
                overlay_duration = float(overlay.duration)
                st.info(f"Overlay trimmed to: {overlay_duration:.1f} seconds")
                
                orig_width, orig_height = overlay.size
                orig_width, orig_height = int(orig_width), int(orig_height)
                st.info(f"Original video: {orig_width} × {orig_height}, {overlay.duration:.1f}s")
                
                # Handle duration matching
                if overlay_duration < audio_duration:
                    # Loop video
                    loops = int(np.ceil(audio_duration / overlay_duration))
                    overlay_loops = []
                    for _ in range(loops):
                        overlay_copy = overlay.copy()
                        overlay_loops.append(overlay_copy)
                    overlay = concatenate_videoclips(overlay_loops)
                    overlay = overlay.subclip(0, audio_duration)
                elif overlay_duration > audio_duration:
                    overlay = overlay.subclip(0, audio_duration)
                
                # Ensure we have the updated duration
                overlay_duration = float(overlay.duration)
                
                # Resize video based on fit option
                screen_ratio = float(SCREEN_WIDTH) / float(SCREEN_HEIGHT)
                video_ratio = float(orig_width) / float(orig_height)
                
                if fit_option == "Fill Screen (Crop if needed)":
                    # Crop to fill
                    if video_ratio > screen_ratio:
                        # Video wider than screen - crop sides
                        crop_width = int(float(orig_height) * screen_ratio)
                        x_center = orig_width // 2
                        # Ensure integer crop coordinates
                        x1 = int(x_center - crop_width//2)
                        x2 = int(x_center + crop_width//2)
                        overlay = overlay.crop(x1=x1, x2=x2)
                    else:
                        # Video taller than screen - crop top/bottom
                        crop_height = int(float(orig_width) / screen_ratio)
                        y_center = orig_height // 2
                        # Ensure integer crop coordinates
                        y1 = int(y_center - crop_height//2)
                        y2 = int(y_center + crop_height//2)
                        overlay = overlay.crop(y1=y1, y2=y2)
                    
                    # Ensure integer dimensions for resize
                    overlay = overlay.resize((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)))
                    
                elif fit_option == "Fit Entire (Keep all content)":
                    # Fit with black bars
                    if video_ratio > screen_ratio:
                        # Fit to width
                        overlay = overlay.resize(width=int(SCREEN_WIDTH))
                    else:
                        # Fit to height
                        overlay = overlay.resize(height=int(SCREEN_HEIGHT))
                    
                    # Create black background with integer dimensions
                    background = ColorClip((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)), color=(0, 0, 0), duration=overlay.duration)
                    # Position overlay
                    overlay = overlay.set_position('center')
                    overlay = CompositeVideoClip([background, overlay], size=(int(SCREEN_WIDTH), int(SCREEN_HEIGHT)))
                    
                else:  # "Stretch to Fit"
                    # Stretch video with integer dimensions
                    overlay = overlay.resize((int(SCREEN_WIDTH), int(SCREEN_HEIGHT)))
            
            # ----- STEP 3: ADD AUDIO TO OVERLAY -----
            st.info("🎥 Adding audio...")
            
            # If overlay is already a CompositeVideoClip (from fit entire), extract the actual overlay
            if isinstance(overlay, CompositeVideoClip):
                # Get the actual video from composite
                overlay_with_audio = overlay.set_audio(audio_clip)
                final_video = overlay_with_audio
            else:
                # Regular overlay
                overlay = overlay.set_audio(audio_clip)
                final_video = overlay
            
            final_video = final_video.set_duration(audio_duration)
            final_video = final_video.set_fps(30)
            
            # ----- STEP 4: SAVE VIDEO -----
            st.info("💾 Saving video...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Optimize for mobile
            final_video.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                bitrate="10M",  # Higher bitrate for quality
                verbose=False,
                logger=None,
                threads=2,
                preset='medium',
                ffmpeg_params=['-movflags', '+faststart']  # For mobile playback
            )
            
            # Cleanup
            audio_clip.close()
            if isinstance(overlay, CompositeVideoClip):
                for clip in overlay.clips:
                    try:
                        clip.close()
                    except:
                        pass
            else:
                try:
                    overlay.close()
                except:
                    pass
            final_video.close()
            
            # Cleanup temp files
            if 'temp_img_path' in locals():
                try:
                    os.unlink(temp_img_path)
                except:
                    pass
            
            st.success(f"✅ Fullscreen video created!")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Technical details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 5: SHOW RESULT -----
    st.subheader("📱 Your Fullscreen Video")
    
    # Show preview in phone frame
    preview_width = min(400, SCREEN_WIDTH)
    preview_height = int(float(preview_width) * (float(SCREEN_HEIGHT) / float(SCREEN_WIDTH)))
    
    phone_frame_html = f"""
    <div style="
        width: {preview_width}px;
        height: {preview_height}px;
        margin: 20px auto;
        border: 12px solid #222;
        border-radius: 40px;
        overflow: hidden;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        background: black;
        position: relative;
    ">
    <div style="
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 6px;
        background: #333;
        border-radius: 0 0 10px 10px;
    "></div>
    """
    st.markdown(phone_frame_html, unsafe_allow_html=True)
    
    # Video preview
    try:
        st.video(output_path)
    except:
        st.info("💡 Preview below - download for full quality")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Video info
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Duration", f"{audio_duration:.1f}s")
        st.metric("Resolution", f"{SCREEN_WIDTH}×{SCREEN_HEIGHT}")
    with col_info2:
        st.metric("Audio Range", f"{audio_start:.1f}s - {audio_end:.1f}s")
        st.metric("Fit Mode", fit_option)
    with col_info3:
        if not st.session_state.overlay_is_image:
            st.metric("Overlay Range", f"{overlay_start:.1f}s - {overlay_end:.1f}s")
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        st.metric("File Size", f"{file_size:.1f} MB")
    
    # Download
    with open(output_path, "rb") as f:
        st.download_button(
            f"⬇ Download Fullscreen Video ({file_size:.1f} MB)",
            f,
            file_name=f"fullscreen_{SCREEN_WIDTH}x{SCREEN_HEIGHT}.mp4",
            mime="video/mp4",
            type="primary"
        )

else:
    # Show instructions
    st.markdown("""
    ## 📱 Create Fullscreen Mobile Videos
    
    ### How it works:
    1. **Upload Background** - Any audio/video file (only audio used)
    2. **Upload Overlay** - Image or video (will fill entire screen)
    3. **Adjust Durations** - Use sliders to select exact segments
    4. **Choose Fit Option** - How overlay fits on screen
    5. **Click Create** - Get fullscreen mobile video
    
    ### 🎨 Fit Options Explained:
    - **Fill Screen** - Crops edges to fill screen completely
    - **Fit Entire** - Shows entire content (black bars if needed)
    - **Stretch to Fit** - Stretches to fill (may distort)
    
    ### 📱 Perfect for:
    - Instagram Reels/TikTok with specific music cues
    - YouTube Shorts with timed overlays
    - Instagram Stories with trimmed videos
    - Mobile wallpaper videos
    """)

# ---------- CLEANUP FUNCTION ----------
def cleanup_resources():
    """Cleanup all temporary files"""
    files_to_cleanup = []
    
    # Add all temp files from session state
    if st.session_state.bg_path and os.path.exists(st.session_state.bg_path):
        files_to_cleanup.append(st.session_state.bg_path)
    if st.session_state.overlay_path and os.path.exists(st.session_state.overlay_path):
        files_to_cleanup.append(st.session_state.overlay_path)
    if st.session_state.bg_preview_path and os.path.exists(st.session_state.bg_preview_path):
        files_to_cleanup.append(st.session_state.bg_preview_path)
    if st.session_state.overlay_preview_path and os.path.exists(st.session_state.overlay_preview_path):
        files_to_cleanup.append(st.session_state.overlay_preview_path)
    
    # Close clips
    if st.session_state.bg_clip:
        try:
            st.session_state.bg_clip.close()
        except:
            pass
    if st.session_state.overlay_clip:
        try:
            st.session_state.overlay_clip.close()
        except:
            pass
    if st.session_state.bg_audio_clip:
        try:
            st.session_state.bg_audio_clip.close()
        except:
            pass
    
    # Delete files
    for file in files_to_cleanup:
        try:
            os.unlink(file)
        except:
            pass

# Register cleanup on app exit
import atexit
atexit.register(cleanup_resources)
