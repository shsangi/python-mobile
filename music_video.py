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
    ColorClip
)

# ---------- CUSTOM RESIZE FUNCTION ----------
def resize_clip(clip, height=None, width=None):
    """
    Custom resize function that works around MoviePy's deprecated ANTIALIAS issue.
    """
    if height is None and width is None:
        return clip
    
    # Get original dimensions
    original_width, original_height = clip.size
    
    # Calculate new dimensions
    if height is not None and width is not None:
        new_width, new_height = width, height
    elif height is not None:
        new_height = height
        new_width = int(original_width * (height / original_height))
    else:  # width is not None
        new_width = width
        new_height = int(original_height * (width / original_width))
    
    # Ensure dimensions are integers
    new_width, new_height = int(new_width), int(new_height)
    
    # Create a custom transformation function
    def transform_frame(frame):
        # Convert numpy array to PIL Image
        pil_img = Image.fromarray(frame)
        
        # Use modern resampling method
        if hasattr(Image, 'Resampling'):
            resample_method = Image.Resampling.LANCZOS
        elif hasattr(Image, 'LANCZOS'):
            resample_method = Image.LANCZOS
        else:
            resample_method = Image.ANTIALIAS
        
        # Resize the image
        resized_img = pil_img.resize((new_width, new_height), resample_method)
        
        # Convert back to numpy array
        return np.array(resized_img)
    
    # Apply the transformation to the clip
    return clip.fl_image(transform_frame)

# ---------- PAGE ----------
st.set_page_config(page_title="Simple Video Maker", layout="centered")
st.title("🎬 Mobile Video Maker")
st.caption("Create vertical videos for mobile platforms (Instagram Reels, TikTok, YouTube Shorts)")

# ---------- VERSION INFO ----------
st.subheader("📦 Environment Versions")
st.code(f"""
MoviePy        : {moviepy.__version__}
Decorator      : {decorator.__version__}
FFmpeg (path)  : {imageio_ffmpeg.get_ffmpeg_exe()}
Pillow         : {Image.__version__}
""")

# ---------- MOBILE VIDEO SETTINGS ----------
st.subheader("📱 Mobile Video Settings")

# Let user choose mobile aspect ratio
aspect_ratio = st.selectbox(
    "Select Mobile Aspect Ratio",
    ["9:16 (Instagram Reels/TikTok)", "1:1 (Instagram Square)", "4:5 (Instagram Portrait)", "Custom"]
)

if aspect_ratio == "9:16 (Instagram Reels/TikTok)":
    WIDTH, HEIGHT = 1080, 1920  # Vertical 9:16
    overlay_height = 800  # Larger overlay for vertical videos
elif aspect_ratio == "1:1 (Instagram Square)":
    WIDTH, HEIGHT = 1080, 1080  # Square
    overlay_height = 700
elif aspect_ratio == "4:5 (Instagram Portrait)":
    WIDTH, HEIGHT = 1080, 1350  # Portrait
    overlay_height = 750
else:  # Custom
    WIDTH = st.number_input("Width (pixels)", min_value=480, max_value=3840, value=1080)
    HEIGHT = st.number_input("Height (pixels)", min_value=480, max_value=3840, value=1920)
    overlay_height = st.slider("Overlay Height", min_value=200, max_value=1000, value=800)

# Overlay position options
overlay_position = st.selectbox(
    "Overlay Position",
    ["Center", "Top", "Bottom", "Custom Position"]
)

if overlay_position == "Custom Position":
    pos_x = st.slider("Horizontal Position (0=left, 1=right)", 0.0, 1.0, 0.5, 0.01)
    pos_y = st.slider("Vertical Position (0=top, 1=bottom)", 0.0, 1.0, 0.5, 0.01)
    custom_position = (pos_x, pos_y)
else:
    position_map = {
        "Center": "center",
        "Top": ("center", "top"),
        "Bottom": ("center", "bottom")
    }
    custom_position = position_map.get(overlay_position, "center")

# ---------- UPLOADS ----------
st.subheader("📁 Upload Files")

bg_file = st.file_uploader(
    "Background (Video or Audio)",
    type=["mp4", "mov", "avi", "mp3", "wav", "mpeg4"],
    help="Upload a video background or audio only (for audio-only, a black background will be used)"
)

overlay_file = st.file_uploader(
    "Overlay (Image or Video)",
    type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "mpeg4"],
    help="Upload an image or video to overlay on top of the background"
)

# ---------- PROCESS ----------
if st.button("🎥 Create Mobile Video", type="primary") and bg_file and overlay_file:

    with st.spinner("Creating mobile video..."):
        # Create temp files
        def save_temp(upload):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.name)[1])
            f.write(upload.read())
            f.close()
            return f.name

        bg_path = save_temp(bg_file)
        ov_path = save_temp(overlay_file)

        TARGET_FPS = 30  # Higher FPS for smoother mobile videos

        try:
            # ----- BACKGROUND -----
            if bg_file.type.startswith("video"):
                bg = VideoFileClip(bg_path)
                bg = bg.set_fps(TARGET_FPS)
                
                # For mobile: crop background to fit vertical aspect ratio
                if bg.size[0] / bg.size[1] > WIDTH / HEIGHT:  # Background is wider than target
                    # Crop sides to fit vertical
                    crop_width = bg.size[1] * (WIDTH / HEIGHT)
                    x_center = bg.size[0] / 2
                    bg = bg.crop(x1=x_center - crop_width/2, x2=x_center + crop_width/2)
                else:  # Background is taller than target
                    # Crop top/bottom to fit vertical
                    crop_height = bg.size[0] * (HEIGHT / WIDTH)
                    y_center = bg.size[1] / 2
                    bg = bg.crop(y1=y_center - crop_height/2, y2=y_center + crop_height/2)
                
                # Resize to target mobile dimensions
                bg = resize_clip(bg, width=WIDTH, height=HEIGHT)
            else:
                # Audio-only background for mobile
                audio = AudioFileClip(bg_path)
                # Create gradient background for mobile (more appealing than plain black)
                bg = ColorClip(
                    (WIDTH, HEIGHT), 
                    color=(20, 20, 30),  # Dark blue-gray instead of pure black
                    duration=audio.duration
                )
                bg = bg.set_audio(audio).set_fps(TARGET_FPS)

            # ----- OVERLAY -----
            if overlay_file.type.startswith("image"):
                # Load and resize image for mobile
                pil_img = Image.open(ov_path)
                original_width, original_height = pil_img.size
                
                # Calculate new size maintaining aspect ratio
                new_height = overlay_height
                new_width = int(original_width * (new_height / original_height))
                
                # Ensure width doesn't exceed video width
                if new_width > WIDTH * 0.9:  # Max 90% of video width
                    new_width = int(WIDTH * 0.9)
                    new_height = int(original_height * (new_width / original_width))
                
                # Ensure dimensions are at least 1
                new_width, new_height = max(1, new_width), max(1, new_height)
                
                # Resize using modern Pillow method
                if hasattr(Image, 'Resampling'):
                    resized_img = pil_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                elif hasattr(Image, 'LANCZOS'):
                    resized_img = pil_img.resize((new_width, new_height), Image.LANCZOS)
                else:
                    resized_img = pil_img.resize((new_width, new_height), Image.ANTIALIAS)
                
                # Save resized image to temp file
                temp_img_path = os.path.join(tempfile.gettempdir(), "resized_overlay.png")
                resized_img.save(temp_img_path, format="PNG")
                
                # Create ImageClip from resized image
                ov = ImageClip(temp_img_path).set_duration(bg.duration)
                
            else:
                # Load video overlay
                ov = VideoFileClip(ov_path).set_fps(TARGET_FPS)
                
                # Resize for mobile
                ov = resize_clip(ov, height=overlay_height)
                
                # Match duration with background
                if ov.duration > bg.duration:
                    ov = ov.subclip(0, bg.duration)
                elif ov.duration < bg.duration:
                    # Loop video overlay if it's shorter than background
                    ov = ov.loop(duration=bg.duration)
            
            # Position overlay for mobile
            if isinstance(custom_position, tuple) and len(custom_position) == 2:
                if isinstance(custom_position[0], float) and isinstance(custom_position[1], float):
                    # Custom position as percentages
                    pos_x_pixels = int((WIDTH - ov.size[0]) * custom_position[0])
                    pos_y_pixels = int((HEIGHT - ov.size[1]) * custom_position[1])
                    ov = ov.set_position((pos_x_pixels, pos_y_pixels))
                else:
                    ov = ov.set_position(custom_position)
            else:
                ov = ov.set_position(custom_position)
            
            ov = ov.set_fps(TARGET_FPS)
            
            # Ensure both clips have the same duration
            min_duration = min(bg.duration, ov.duration)
            bg = bg.subclip(0, min_duration)
            ov = ov.subclip(0, min_duration)

            # ----- FINAL MOBILE VIDEO -----
            final = CompositeVideoClip(
                [bg, ov],
                size=(WIDTH, HEIGHT)
            ).set_fps(TARGET_FPS)

            output = os.path.join(tempfile.gettempdir(), "mobile_video.mp4")
            
            # Optimize for mobile with higher quality settings
            final.write_videofile(
                output,
                codec="libx264",
                audio_codec="aac",
                fps=TARGET_FPS,
                bitrate="5M",  # Higher bitrate for mobile quality
                threads=4,
                logger=None,
                temp_audiofile=os.path.join(tempfile.gettempdir(), "temp_audio.m4a"),
                remove_temp=True,
                preset='medium',  # Encoding preset
                ffmpeg_params=['-movflags', '+faststart']  # Optimize for streaming
            )
            
            # Clean up temp image file if it exists
            if 'temp_img_path' in locals() and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except:
                    pass
                
        except Exception as e:
            st.error(f"❌ Error creating mobile video: {str(e)}")
            import traceback
            st.code(traceback.format_exc())
            st.info("""
            **Troubleshooting Tips:**
            1. Try converting files to MP4 format
            2. Use shorter video clips
            3. Check file sizes (keep under 100MB)
            4. Try different aspect ratios
            """)
            st.stop()
        finally:
            # Clean up uploaded temp files
            for path in [bg_path, ov_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

    st.success(f"✅ Mobile video created successfully!")
    st.info(f"**Dimensions:** {WIDTH}×{HEIGHT} | **FPS:** {TARGET_FPS} | **Duration:** {min_duration:.1f}s")
    
    # Show video preview
    try:
        st.subheader("📱 Video Preview")
        # Create a container with mobile-like dimensions
        preview_html = f"""
        <div style="
            width: {min(400, WIDTH)}px;
            height: {min(700, HEIGHT)}px;
            margin: 0 auto;
            border: 2px solid #ddd;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            background: black;
        ">
        """
        st.markdown(preview_html, unsafe_allow_html=True)
        st.video(output)
        st.markdown("</div>", unsafe_allow_html=True)
    except:
        st.info("Video preview unavailable. You can still download the file.")
    
    # Download section
    st.subheader("📥 Download Video")
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            with open(output, "rb") as f:
                file_size = os.path.getsize(output) / (1024*1024)  # MB
                st.download_button(
                    f"⬇ Download ({file_size:.1f} MB)",
                    f,
                    file_name=f"mobile_video_{WIDTH}x{HEIGHT}.mp4",
                    mime="video/mp4",
                    type="primary"
                )
        except Exception as e:
            st.error(f"Error preparing download: {str(e)}")
    
    with col2:
        # Quick share suggestions
        st.caption("**Perfect for:**")
        st.caption("📱 Instagram Reels")
        st.caption("🎵 TikTok")
        st.caption("▶️ YouTube Shorts")
        st.caption("📘 Facebook Stories")

# ---------- MOBILE VIDEO TIPS ----------
with st.expander("📱 Mobile Video Tips"):
    st.markdown("""
    ### **Best Practices for Mobile Videos:**
    
    **📏 Aspect Ratios:**
    - **9:16** - Instagram Reels, TikTok, YouTube Shorts
    - **1:1** - Instagram Posts, Facebook
    - **4:5** - Instagram Portrait
    
    **🎬 Content Tips:**
    1. **Vertical is best** - Mobile users hold phones vertically
    2. **Keep it short** - 15-60 seconds works best
    3. **Center important content** - Avoid edges
    4. **Use bold text** - Small screens need clear text
    
    **⚙️ Technical Tips:**
    - Use **MP4 format** for best compatibility
    - **1080×1920** is ideal for vertical videos
    - **30 FPS** provides smooth playback
    - Keep file size under **100MB** for easy sharing
    """)

# ---------- EXAMPLE LAYOUTS ----------
with st.expander("🎨 Example Layouts"):
    st.markdown("""
    ### **Popular Mobile Video Layouts:**
    
    **1. Story Style (Top + Bottom Content)**
    ```
    ┌─────────────────┐
    │     TITLE       │ ← Top text/logo
    │                 │
    │                 │
    │    CONTENT      │ ← Main video/image
    │                 │
    │                 │
    │   CAPTION       │ ← Bottom text/CTA
    └─────────────────┘
    ```
    
    **2. Centered Focus**
    ```
    ┌─────────────────┐
    │                 │
    │                 │
    │                 │
    │    [MAIN]       │ ← Center content
    │                 │
    │                 │
    │                 │
    └─────────────────┘
    ```
    
    **3. Brand Overlay**
    ```
    ┌─────────────────┐
    │    LOGO         │ ← Small logo top-left
    │                 │
    │      MAIN       │
    │    CONTENT      │
    │                 │
    │  @username      │ ← Handle bottom-left
    └─────────────────┘
    ```
    """)
