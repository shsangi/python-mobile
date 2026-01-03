import streamlit as st 
import tempfile
import os
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.VideoClip import ColorClip
import cv2
import mimetypes

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
    # Get file extension
    _, ext = os.path.splitext(f.name)
    if not ext:
        # Try to guess extension from mimetype
        mime_type = getattr(f, 'type', '')
        ext = mimetypes.guess_extension(mime_type) or ''
    
    # Use .tmp extension if no extension found
    suffix = ext if ext else '.tmp'
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(f.getvalue())
    tmp.close()
    return tmp.name

def is_audio_file(file_path):
    """Check if file is an audio file based on extension and content"""
    audio_extensions = {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.opus', 
                       '.mp4', '.mov', '.avi', '.mkv', '.webm'}  # Video files that can contain audio
    
    # Check extension
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    if ext in {'.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma', '.opus'}:
        return True
    
    # For video files, check if it has audio
    if ext in {'.mp4', '.mov', '.avi', '.mkv', '.webm'}:
        try:
            clip = VideoFileClip(file_path)
            has_audio = clip.audio is not None
            clip.close()
            return has_audio
        except:
            return False
    
    return False

def is_video_file(file_path):
    """Check if file is a video file"""
    video_extensions = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv', '.mpeg', '.mpg'}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in video_extensions

def is_image_file(file_path):
    """Check if file is an image file"""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    _, ext = os.path.splitext(file_path)
    return ext.lower() in image_extensions

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
    st.markdown("**Background Audio/Voice**")
    bg = st.file_uploader(
        "Upload any audio/voice file",
        type=None,  # Accept all file types
        accept_multiple_files=False,
        help="Supported formats: MP3, WAV, M4A, AAC, FLAC, OGG, WMA, OPUS, MP4 (audio), MOV (audio), etc."
    )
    
    if bg:
        try:
            bg_path = save_file(bg)
            
            # Determine file type
            if is_video_file(bg_path):
                # Try to load as video first
                try:
                    clip = VideoFileClip(bg_path)
                    if clip.audio is not None:
                        audio = clip.audio
                        st.session_state.bg_dur = float(audio.duration)
                        st.success(f"✅ Video with audio: {bg.name} ({audio.duration:.1f}s)")
                    else:
                        # Video without audio, try as audio file
                        clip.close()
                        try:
                            audio = AudioFileClip(bg_path)
                            st.session_state.bg_dur = float(audio.duration)
                            st.success(f"✅ Audio: {bg.name} ({audio.duration:.1f}s)")
                        except:
                            st.error(f"❌ {bg.name} has no audio track")
                            bg = None
                except Exception as e:
                    st.error(f"❌ Cannot load video file: {e}")
                    bg = None
            
            elif is_audio_file(bg_path):
                try:
                    audio = AudioFileClip(bg_path)
                    st.session_state.bg_dur = float(audio.duration)
                    st.session_state.a_trim = [0.0, min(30.0, float(audio.duration))]
                    st.success(f"✅ Audio: {bg.name} ({audio.duration:.1f}s)")
                except Exception as e:
                    st.error(f"❌ Cannot load audio file: {e}")
                    bg = None
            
            else:
                st.error(f"❌ Unsupported file type: {bg.name}")
                bg = None
                
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
            bg = None

with c2:
    st.markdown("**Overlay (Video/Image)**")
    ov = st.file_uploader(
        "Upload video or image",
        type=["mp4", "mov", "avi", "mkv", "webm", "jpg", "jpeg", "png", "gif", "bmp", "webp"],
        help="Supported: Videos (MP4, MOV, AVI, etc.) and Images (JPG, PNG, GIF, etc.)"
    )
    if ov:
        ov_path = save_file(ov)
        is_img = is_image_file(ov_path)
        if is_img:
            try:
                img = Image.open(ov_path)
                st.image(img, width=300)
                st.success(f"✅ Image: {ov.name}")
            except Exception as e:
                st.error(f"❌ Cannot load image: {e}")
                ov = None
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
                st.error(f"❌ Cannot load video: {e}")
                ov = None

# Audio trim
if bg and st.session_state.bg_dur > 0:
    st.subheader("Audio Selection")
    a_trim = st.slider("Audio range", 0.0, float(st.session_state.bg_dur), 
                      tuple(map(float, st.session_state.a_trim)), 0.5, format="%.1fs")
    st.session_state.a_trim = list(a_trim)
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(a_trim[0]))
    c2.metric("End", fmt_time(a_trim[1]))
    c3.metric("Duration", fmt_time(a_trim[1] - a_trim[0]))

# Video/Image overlay settings
if ov and not is_img and st.session_state.ov_dur > 0:
    st.subheader("Video Overlay")
    v_trim = st.slider("Video range", 0.0, float(st.session_state.ov_dur), 
                      tuple(map(float, st.session_state.v_trim)), 0.5, format="%.1fs")
    st.session_state.v_trim = list(v_trim)
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(v_trim[0]))
    c2.metric("End", fmt_time(v_trim[1]))
    c3.metric("Duration", fmt_time(v_trim[1] - v_trim[0]))
elif ov and is_img and st.session_state.bg_dur > 0:
    st.subheader("Image Duration")
    max_dur = st.session_state.a_trim[1] - st.session_state.a_trim[0]
    st.session_state.img_dur = st.slider("Display time", 1.0, float(max_dur), 
                                        min(30.0, float(max_dur)), 0.5, format="%.1fs")

# Output format selection
if bg and ov:
    st.subheader("📐 Output Format")
    selected_preset = st.selectbox("Choose output dimensions", list(PRESETS.keys()), index=0)
    target_dims = PRESETS[selected_preset]
    
    if target_dims:
        st.info(f"Will resize to: {target_dims[0]}×{target_dims[1]} (adds black bars to maintain aspect ratio)")
    else:
        st.info("Original dimensions will be preserved")

# Process button
st.divider()
if st.button("🎬 Create Video", type="primary", disabled=not (bg and ov), use_container_width=True):
    try:
        with st.spinner("Processing video..."):
            # Extract audio from background file
            is_vid = is_video_file(bg_path)
            try:
                if is_vid:
                    clip = VideoFileClip(bg_path)
                    audio_src = clip
                else:
                    audio_src = AudioFileClip(bg_path)
                
                audio = audio_src.audio.subclip(*st.session_state.a_trim) if is_vid else audio_src.subclip(*st.session_state.a_trim)
                dur = audio.duration
                
            except Exception as e:
                st.error(f"❌ Error loading audio: {e}")
                raise
            
            # Process overlay
            if is_img:
                try:
                    img = Image.open(ov_path)
                    img_arr = np.array(img)
                    
                    # Resize image if target dims specified
                    if target_dims:
                        img_arr = resize_frame(img_arr, target_dims)
                    
                    img_dur = min(st.session_state.img_dur, dur)
                    ov_final = ImageClip(img_arr, duration=img_dur)
                    
                    if img_dur < dur:
                        bg_clip = ColorClip(size=ov_final.size, color=(0,0,0), duration=dur)
                        ov_final = CompositeVideoClip([bg_clip, ov_final.set_position('center')], duration=dur)
                except Exception as e:
                    st.error(f"❌ Error processing image: {e}")
                    raise
            else:
                try:
                    ov_final = VideoFileClip(ov_path, audio=False).subclip(*st.session_state.v_trim)
                    
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
                except Exception as e:
                    st.error(f"❌ Error processing video overlay: {e}")
                    raise
            
            # Create final video
            final = ov_final.set_audio(audio).set_duration(dur)
            out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            final.write_videofile(
                out, 
                fps=30,
                codec="libx264", 
                audio_codec="aac", 
                bitrate="8M", 
                verbose=False, 
                logger=None,
                preset='medium'
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
                ov_final.close()
            if is_vid:
                audio_src.close()
            else:
                audio_src.close()
            final.close()
        except:
            pass
        
        try:
            os.unlink(bg_path)
            os.unlink(ov_path)
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())