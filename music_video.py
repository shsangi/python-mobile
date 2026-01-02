import streamlit as st 
import tempfile
import os
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.VideoClip import ColorClip
import cv2
import subprocess

st.set_page_config(page_title="🎬 Mobile Video Maker v2", layout="centered")
st.markdown('<style>[data-testid="stSidebar"]{display:none}.stButton>button{width:100%}</style>', unsafe_allow_html=True)
st.title("🎬 Mobile Video Maker")
st.caption("Combine audio with video - Choose your output format")

# Preset dimensions for mobile
PRESETS = {
    "Original (No Change)": None,
    "📱 9:16 Portrait (1080x1920) - Instagram Reels/TikTok": (1080, 1920),
    "📱 9:16 Portrait (720x1280) - Standard Mobile": (720, 1280),
    "📺 16:9 Landscape (1920x1080) - YouTube": (1920, 1080),
    "📺 16:9 Landscape (1280x720) - Standard HD": (1280, 720),
    "⬜ 1:1 Square (1080x1080) - Instagram Post": (1080, 1080),
    "⬜ 4:5 Portrait (1080x1350) - Instagram": (1080, 1350),
    "📱 9:16 Portrait (540x960) - Small/Fast": (540, 960),
}

# Initialize session state
for k, v in {'bg_dur': 0.0, 'ov_dur': 0.0, 'a_trim': [0.0, 30.0], 'v_trim': [0.0, 30.0], 'img_dur': 5.0}.items():
    st.session_state.setdefault(k, v)

def save_file(f):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1])
    tmp.write(f.getvalue())
    tmp.close()
    return tmp.name

def convert_audio_to_wav(input_path):
    """Convert problematic audio formats to WAV using FFmpeg"""
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.wav').name
    
    try:
        # Try to convert using FFmpeg
        cmd = [
            'ffmpeg', '-i', input_path,
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            '-y',  # Overwrite output file
            output_path
        ]
        
        # Run FFmpeg
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            st.error(f"FFmpeg conversion failed: {result.stderr}")
            return input_path  # Return original if conversion fails
        
        return output_path
    except Exception as e:
        st.warning(f"Audio conversion failed, using original: {e}")
        return input_path

def fmt_time(s):
    return f"{int(s//60):02d}:{int(s%60):02d}" if s < 3600 else f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"

def resize_frame(frame, target_size):
    """Resize frame using cv2 (no PIL issues)"""
    target_w, target_h = target_size
    h, w = frame.shape[:2]
    
    # Calculate scale to fit inside target
    scale = min(target_w / w, target_h / h)
    new_w, new_h = int(w * scale), int(h * scale)
    
    # Make even
    new_w = new_w if new_w % 2 == 0 else new_w - 1
    new_h = new_h if new_h % 2 == 0 else new_h - 1
    
    # Resize using cv2
    resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    # Create black canvas
    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
    
    # Center the resized frame
    y_offset = (target_h - new_h) // 2
    x_offset = (target_w - new_w) // 2
    canvas[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
    
    return canvas

def apply_resize_to_clip(clip, target_size):
    """Apply resize to every frame using cv2"""
    return clip.fl_image(lambda frame: resize_frame(frame, target_size))

# Upload section
c1, c2 = st.columns(2)

with c1:
    # ALL audio formats including call recording formats
    bg = st.file_uploader("Background Audio/Video", 
                         type=[
                             # Common audio formats
                             "mp3", "wav", "m4a", 
                             # Call recording formats
                             "aac", "opus", "ogg", "amr", "3gp",
                             # Video formats (may contain audio)
                             "mp4", "mov", "avi", "mkv", "webm"
                         ])
    if bg:
        bg_path = save_file(bg)
        
        # Check file type
        file_ext = os.path.splitext(bg.name.lower())[1]
        
        # Problematic formats that might need conversion
        problematic_formats = ['.aac', '.opus', '.amr', '.3gp', '.ogg']
        
        if file_ext in problematic_formats:
            st.info(f"🔄 Converting {file_ext} audio file for compatibility...")
            converted_path = convert_audio_to_wav(bg_path)
            
            if converted_path != bg_path:
                # Update to use converted file
                bg_path = converted_path
                st.success(f"✅ Converted {bg.name} to WAV for compatibility")
        
        # Determine if it's video or audio
        video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
        is_vid = file_ext in video_extensions
        
        try:
            if is_vid:
                clip = VideoFileClip(bg_path)
                audio = clip.audio
                if audio:
                    st.session_state.bg_dur = float(audio.duration)
                    st.session_state.a_trim = [0.0, min(30.0, float(audio.duration))]
                    st.success(f"✅ {bg.name} (Video with audio: {audio.duration:.1f}s)")
                else:
                    st.error("❌ No audio track found in video file")
                    bg = None
            else:
                # Try to load as audio
                try:
                    audio = AudioFileClip(bg_path)
                    st.session_state.bg_dur = float(audio.duration)
                    st.session_state.a_trim = [0.0, min(30.0, float(audio.duration))]
                    st.success(f"✅ {bg.name} (Audio: {audio.duration:.1f}s)")
                except Exception as e:
                    st.error(f"❌ Cannot read audio file: {e}")
                    st.info("Trying alternative loading method...")
                    # Try with explicit audio codec
                    try:
                        audio = AudioFileClip(bg_path, fps=44100)
                        st.session_state.bg_dur = float(audio.duration)
                        st.session_state.a_trim = [0.0, min(30.0, float(audio.duration))]
                        st.success(f"✅ {bg.name} loaded with fallback (Audio: {audio.duration:.1f}s)")
                    except:
                        st.error("❌ Failed to load audio file. Try converting it to MP3 or WAV first.")
                        bg = None
        except Exception as e:
            st.error(f"❌ Error loading file: {e}")
            bg = None
        
with c2:
    ov = st.file_uploader("Overlay (Video/Image)", 
                         type=["mp4", "mov", "avi", "mkv", "webm",
                               "jpg", "jpeg", "png", "gif", "bmp", "webp"])
    if ov:
        ov_path = save_file(ov)
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
        file_ext = os.path.splitext(ov.name.lower())[1]
        is_img = file_ext in image_extensions
        
        if is_img:
            img = Image.open(ov_path)
            st.image(img, width=300)
            st.success(f"✅ Image: {ov.name}")
        else:
            try:
                ov_clip = VideoFileClip(ov_path, audio=False)
                st.session_state.ov_dur = float(ov_clip.duration)
                st.session_state.v_trim = [0.0, min(30.0, float(ov_clip.duration))]
                w, h = ov_clip.size
                orientation = "Portrait" if h > w else "Landscape" if w > h else "Square"
                st.success(f"✅ Video: {ov.name} ({ov_clip.duration:.1f}s)")
                st.info(f"📐 {w}×{h} ({orientation})")
            except Exception as e:
                st.error(f"❌ Error loading video: {e}")
                ov = None

# Audio trim
if 'bg' in locals() and bg and st.session_state.bg_dur > 0:
    st.subheader("Audio Selection")
    a_trim = st.slider("Audio range", 0.0, float(st.session_state.bg_dur), 
                      tuple(map(float, st.session_state.a_trim)), 0.5, format="%.1fs")
    st.session_state.a_trim = list(a_trim)
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(a_trim[0]))
    c2.metric("End", fmt_time(a_trim[1]))
    c3.metric("Duration", fmt_time(a_trim[1] - a_trim[0]))

# Video/Image overlay settings
if 'ov' in locals() and ov and 'is_img' in locals():
    if not is_img and st.session_state.ov_dur > 0:
        st.subheader("Video Overlay")
        v_trim = st.slider("Video range", 0.0, float(st.session_state.ov_dur), 
                          tuple(map(float, st.session_state.v_trim)), 0.5, format="%.1fs")
        st.session_state.v_trim = list(v_trim)
        c1, c2, c3 = st.columns(3)
        c1.metric("Start", fmt_time(v_trim[0]))
        c2.metric("End", fmt_time(v_trim[1]))
        c3.metric("Duration", fmt_time(v_trim[1] - v_trim[0]))
    elif is_img and st.session_state.bg_dur > 0:
        st.subheader("Image Duration")
        max_dur = st.session_state.a_trim[1] - st.session_state.a_trim[0]
        st.session_state.img_dur = st.slider("Display time", 1.0, float(max_dur), 
                                           min(30.0, float(max_dur)), 0.5, format="%.1fs")

# Output format selection
if 'bg' in locals() and bg and 'ov' in locals() and ov:
    st.subheader("📐 Output Format")
    selected_preset = st.selectbox("Choose output dimensions", list(PRESETS.keys()), index=0)
    target_dims = PRESETS[selected_preset]
    
    if target_dims:
        st.info(f"Will resize to: {target_dims[0]}×{target_dims[1]} (adds black bars to maintain aspect ratio)")
    else:
        st.info("Original dimensions will be preserved")

# Process button
st.divider()
process_disabled = not ('bg' in locals() and bg and 'ov' in locals() and ov)
if st.button("🎬 Create Video", type="primary", disabled=process_disabled, use_container_width=True):
    try:
        with st.spinner("Processing video..."):
            # Extract audio (use the clip if it's video, otherwise AudioFileClip)
            if is_vid:
                audio_src = clip
                audio = audio_src.audio.subclip(*st.session_state.a_trim)
            else:
                # Reload audio file to ensure fresh handle
                audio_src = AudioFileClip(bg_path)
                audio = audio_src.subclip(*st.session_state.a_trim)
            
            dur = audio.duration
            
            # Process overlay
            if is_img:
                img_arr = np.array(img)
                
                # Resize image if target dims specified
                if target_dims:
                    img_arr = resize_frame(img_arr, target_dims)
                
                img_dur = min(st.session_state.img_dur, dur)
                ov_final = ImageClip(img_arr, duration=img_dur)
                
                if img_dur < dur:
                    bg_clip = ColorClip(size=ov_final.size, color=(0,0,0), duration=dur)
                    ov_final = CompositeVideoClip([bg_clip, ov_final.set_position('center')], duration=dur)
            else:
                ov_final = ov_clip.subclip(*st.session_state.v_trim)
                
                # Loop if needed
                if ov_final.duration < dur:
                    loops = int(dur / ov_final.duration) + 1
                    ov_final = concatenate_videoclips([ov_final] * loops).subclip(0, dur)
                elif ov_final.duration > dur:
                    ov_final = ov_final.subclip(0, dur)
                
                # Apply resize using cv2 if target dims specified
                if target_dims:
                    st.info("⏳ Resizing video frames... this may take a moment")
                    ov_final = apply_resize_to_clip(ov_final, target_dims)
            
            final = ov_final.set_audio(audio).set_duration(dur)
            out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Write with verbose output for debugging
            st.info("⏳ Rendering video...")
            final.write_videofile(
                out, 
                fps=30,
                codec="libx264", 
                audio_codec="aac", 
                bitrate="8M", 
                verbose=False, 
                logger=None,
                preset='medium',
                threads=4
            )
        
        st.success("✅ Video created successfully!")
        st.video(out)
        
        w, h = final.size
        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{dur:.1f}s")
        c2.metric("Resolution", f"{w}×{h}")
        c3.metric("Size", f"{os.path.getsize(out)/(1024*1024):.1f}MB")
        
        format_name = selected_preset.split(" - ")[0].replace("📱 ", "").replace("📺 ", "").replace("⬜ ", "").replace(" ", "_")
        
        with open(out, "rb") as f:
            st.download_button("📥 Download Video", f, f"{format_name}_{w}x{h}.mp4", "video/mp4", type="primary", use_container_width=True)
        
        # Cleanup
        try:
            audio.close()
            if not is_img:
                ov_clip.close()
            if is_vid:
                clip.close()
            else:
                audio_src.close()
            if 'ov_final' in locals():
                ov_final.close()
            if 'final' in locals():
                final.close()
        except:
            pass
        
        # Cleanup temp files
        try:
            if 'bg_path' in locals() and os.path.exists(bg_path):
                os.unlink(bg_path)
            if 'ov_path' in locals() and os.path.exists(ov_path):
                os.unlink(ov_path)
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# Add troubleshooting info
st.divider()
with st.expander("💡 Troubleshooting Audio Files"):
    st.markdown("""
    **Common issues with call recording files:**
    
    1. **AAC/Opus files not working?** 
       - The app tries to automatically convert them to WAV
       - Make sure FFmpeg is installed on your system
    
    2. **If automatic conversion fails:**
       - Convert your audio file to MP3 or WAV first using:
         - Online converters (online-audio-converter.com)
         - VLC media player (Media > Convert/Save)
         - Audacity (free audio editor)
    
    3. **Still having issues?**
       - Try recording in MP3 format if your recording app allows it
       - Use standard formats like MP3 or WAV for best compatibility
    
    **Supported call recording formats:**
    - ✅ `.aac` (Advanced Audio Coding)
    - ✅ `.opus` (Opus audio)
    - ✅ `.amr` (Adaptive Multi-Rate - common for voice recordings)
    - ✅ `.3gp` (3GPP audio/video container)
    - ✅ `.ogg` (Ogg Vorbis)
    """)
