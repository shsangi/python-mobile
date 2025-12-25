import streamlit as st
import tempfile
import os
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
VERSION = "2.1.0"

# ---------- PAGE ----------
st.set_page_config(page_title="Music Video Maker", layout="centered")
st.title(f"🎵 Music Video Maker v{VERSION}")
st.markdown("Combine background (video/audio) with overlay (image/video)")

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
    bg_file = st.file_uploader(
        "Background (Video or Audio)",
        type=["mp4", "mov", "avi", "mp3", "wav", "m4a", "aac", "mpeg4"],
        help="Upload video (with audio) or audio-only file"
    )

with col2:
    overlay_file = st.file_uploader(
        "Overlay (Image or Video)",
        type=["mp4", "mov", "avi", "png", "jpg", "jpeg", "gif"],
        help="Upload image or video to overlay on top"
    )

# ---------- PROCESS ----------
if st.button("🎬 Create Video", type="primary") and bg_file and overlay_file:

    with st.spinner("Creating your video..."):
        
        # Save uploaded files
        def save_temp(upload):
            f = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(upload.name)[1])
            f.write(upload.read())
            f.close()
            return f.name
        
        bg_path = save_temp(bg_file)
        overlay_path = save_temp(overlay_file)
        
        # Video settings
        VIDEO_WIDTH, VIDEO_HEIGHT = 1080, 1920  # Vertical mobile format
        FPS = 30
        
        try:
            # ----- STEP 1: PROCESS BACKGROUND -----
            st.info("🎵 Processing background...")
            
            # Check if file is video or audio
            is_video = bg_file.type.startswith("video") or bg_file.name.lower().endswith(('.mp4', '.mov', '.avi'))
            
            if is_video:
                # Video file (has both video and audio)
                bg_clip = VideoFileClip(bg_path)
                bg_duration = bg_clip.duration
                bg_audio = bg_clip.audio
                
                # If video, we'll use it but make it very dim/transparent
                # Resize to fill screen
                bg_clip = bg_clip.resize((VIDEO_WIDTH, VIDEO_HEIGHT))
                
                # Make video very dim (10% opacity) so overlay is focus
                bg_clip = bg_clip.fl_image(lambda img: (img * 0.1).astype('uint8'))
                
                st.info(f"Video background: {bg_duration:.1f}s")
                
            else:
                # Audio-only file
                bg_audio = AudioFileClip(bg_path)
                bg_duration = bg_audio.duration
                
                # Create simple dark background
                bg_clip = ColorClip(
                    size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                    color=(20, 20, 30),  # Dark blue-gray
                    duration=bg_duration
                )
                bg_clip = bg_clip.set_audio(bg_audio)
                
                st.info(f"Audio background: {bg_duration:.1f}s")
            
            # ----- STEP 2: PROCESS OVERLAY -----
            st.info("🖼️ Processing overlay...")
            
            is_image = overlay_file.type.startswith("image") or overlay_file.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif'))
            
            if is_image:
                # Image overlay
                try:
                    # Load image
                    img = Image.open(overlay_path)
                    img_width, img_height = img.size
                    
                    # Resize to fit nicely (70% of screen height max)
                    max_height = int(VIDEO_HEIGHT * 0.7)
                    if img_height > max_height:
                        scale = max_height / img_height
                        new_width = int(img_width * scale)
                        new_height = max_height
                    else:
                        new_width = img_width
                        new_height = img_height
                    
                    # Ensure not too wide
                    if new_width > VIDEO_WIDTH * 0.9:
                        scale = (VIDEO_WIDTH * 0.9) / new_width
                        new_width = int(new_width * scale)
                        new_height = int(new_height * scale)
                    
                    # Resize
                    if hasattr(Image, 'Resampling'):
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    else:
                        img = img.resize((new_width, new_height), Image.LANCZOS)
                    
                    # Save temp
                    temp_img = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                    img.save(temp_img.name, "PNG")
                    
                    # Create clip
                    overlay = ImageClip(temp_img.name, duration=bg_duration)
                    
                except Exception as e:
                    st.warning(f"Image issue: {e}")
                    # Fallback
                    overlay = ColorClip(
                        size=(500, 500),
                        color=(255, 100, 100),
                        duration=bg_duration
                    )
                    
            else:
                # Video overlay
                try:
                    overlay = VideoFileClip(overlay_path)
                    
                    # Match duration with background
                    if overlay.duration < bg_duration:
                        # Loop if shorter
                        loops = int(bg_duration / overlay.duration) + 1
                        overlay = concatenate_videoclips([overlay] * loops)
                        overlay = overlay.subclip(0, bg_duration)
                    elif overlay.duration > bg_duration:
                        # Trim if longer
                        overlay = overlay.subclip(0, bg_duration)
                        
                except Exception as e:
                    st.warning(f"Video issue: {e}")
                    # Fallback
                    overlay = ColorClip(
                        size=(500, 500),
                        color=(100, 255, 100),
                        duration=bg_duration
                    )
            
            # Resize overlay if needed
            try:
                # Simple resize to 60-80% of screen
                target_size = min(overlay.size[0], overlay.size[1], VIDEO_WIDTH * 0.8, VIDEO_HEIGHT * 0.8)
                if overlay.size[0] > overlay.size[1]:
                    # Wider than tall
                    new_width = int(VIDEO_WIDTH * 0.8)
                    overlay = overlay.resize(width=new_width)
                else:
                    # Taller than wide
                    new_height = int(VIDEO_HEIGHT * 0.7)
                    overlay = overlay.resize(height=new_height)
            except:
                # If resize fails, keep original
                pass
            
            # Position overlay center
            overlay = overlay.set_position("center")
            
            # ----- STEP 3: COMBINE -----
            st.info("🎥 Combining...")
            
            # If background is video, combine with overlay
            # If background is audio-only, we already have it in bg_clip
            
            final_video = CompositeVideoClip(
                [bg_clip, overlay],
                size=(VIDEO_WIDTH, VIDEO_HEIGHT)
            )
            
            # Set duration and FPS
            final_video = final_video.set_duration(bg_duration)
            final_video = final_video.set_fps(FPS)
            
            # If background was video, audio is already attached
            # If background was audio-only, audio is already attached to bg_clip
            
            # ----- STEP 4: SAVE -----
            st.info("💾 Saving...")
            
            output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            final_video.write_videofile(
                output_path,
                fps=FPS,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )
            
            # Cleanup temp files
            temp_files = [bg_path, overlay_path]
            if 'temp_img' in locals():
                temp_files.append(temp_img.name)
            
            for file_path in temp_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except:
                        pass
            
            bg_type = "Video" if is_video else "Audio"
            overlay_type = "Image" if is_image else "Video"
            st.success(f"✅ Video created! ({bg_type} + {overlay_type})")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("See error details"):
                st.code(traceback.format_exc())
            st.stop()
    
    # ----- STEP 5: RESULTS -----
    st.subheader("🎬 Your Video")
    
    # Show video
    try:
        st.video(output_path)
    except:
        st.info("Preview may not show. Download to view.")
    
    # File info
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    
    # Download button
    with open(output_path, "rb") as f:
        st.download_button(
            f"⬇ Download Video ({file_size:.1f} MB)",
            f,
            file_name="my_video.mp4",
            mime="video/mp4",
            type="primary"
        )
    
    # Info
    with st.expander("📊 Video Info"):
        st.write(f"- **Duration**: {bg_duration:.1f} seconds")
        st.write(f"- **Resolution**: {VIDEO_WIDTH} x {VIDEO_HEIGHT}")
        st.write(f"- **FPS**: {FPS}")
        st.write(f"- **Background**: {'Video' if is_video else 'Audio'}")
        st.write(f"- **Overlay**: {'Image' if is_image else 'Video'}")
        st.write(f"- **File Size**: {file_size:.1f} MB")

else:
    # Instructions
    st.markdown("""
    ### How it works:
    1. **Upload Background** - Video (with sound) OR audio-only file
    2. **Upload Overlay** - Image or video to display on top
    3. **Click Create** - Get your combined video
    
    ### Examples:
    - 🎵 Music + 📸 Photo = Music video
    - 🎬 Movie clip + 🖼️ Logo = Branded clip
    - 🎤 Podcast + 📹 Video = Visual podcast
    - 🎼 Song + 🎥 Effects = Enhanced video
    """)

# ---------- SIMPLE FAQ ----------
with st.expander("❓ FAQ"):
    st.markdown("""
    **Q: What if my overlay is shorter than the background?**
    A: Images will show for entire duration. Videos will loop.
    
    **Q: Can I use YouTube videos?**
    A: Upload MP4 files from YouTube downloads.
    
    **Q: What's the maximum duration?**
    A: Depends on file size. Keep under 100MB per file.
    
    **Q: Video is too large?**
    A: Try shorter clips or compress files first.
    
    **Q: Audio not playing?**
    A: Ensure your background file has audio (for video files).
    """)
