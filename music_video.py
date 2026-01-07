import streamlit as st 
import tempfile
import os
from PIL import Image
import numpy as np
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.VideoClip import ColorClip
import cv2
import mimetypes

st.set_page_config(page_title="🎬 PS Video", layout="centered")
st.markdown('<style>[data-testid="stSidebar"]{display:none}.stButton>button{width:100%}</style>', unsafe_allow_html=True)
st.title("🎬 PS Video")

# Initialize session state for output video
if 'output_video_path' not in st.session_state:
    st.session_state.output_video_path = None
if 'output_video_created' not in st.session_state:
    st.session_state.output_video_created = False
if 'output_video_info' not in st.session_state:
    st.session_state.output_video_info = {}

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
for k, v in {'bg_dur': 0.0, 'ov_dur': 0.0, 'a_trim': [0.0, 30.0], 'v_trim': [0.0, 30.0], 'img_dur': 5.0,
             'bg_path': '', 'ov_path': '', 'bg_name': '', 'ov_name': '', 'is_img': False,
             'selected_preset': "Original (No Change)"}.items():
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

# ========== TOP BUTTONS SECTION ==========
st.divider()

# Create two columns for buttons at the top
col1, col2 = st.columns(2)

with col1:
    create_disabled = not (st.session_state.bg_path and st.session_state.ov_path and 
                          os.path.exists(st.session_state.bg_path) and 
                          os.path.exists(st.session_state.ov_path))
    create_btn = st.button("🎬 Create Video", 
                          type="primary", 
                          disabled=create_disabled, 
                          use_container_width=True,
                          key="create_top")

with col2:
    download_disabled = not st.session_state.output_video_created
    if not download_disabled and st.session_state.output_video_path and os.path.exists(st.session_state.output_video_path):
        with open(st.session_state.output_video_path, "rb") as f:
            format_name = st.session_state.output_video_info.get('format_name', 'video')
            w = st.session_state.output_video_info.get('width', 1920)
            h = st.session_state.output_video_info.get('height', 1080)
            st.download_button("📥 Download Video", 
                             f, 
                             f"{format_name}_{w}x{h}.mp4", 
                             "video/mp4", 
                             type="secondary", 
                             use_container_width=True,
                             key="download_top")
    else:
        st.button("📥 Download Video", 
                 disabled=True, 
                 use_container_width=True,
                 help="Create a video first to enable download",
                 key="download_disabled_top")

st.divider()
# ========== END TOP BUTTONS SECTION ==========

# Upload section
c1, c2 = st.columns(2)

with c1:
    bg = st.file_uploader(
        "Upload any audio/voice file",
        type=None,  # Accept all file types
        accept_multiple_files=False,
        help="Supported formats: MP3, WAV, M4A, AAC, FLAC, OGG, WMA, OPUS, MP4 (audio), MOV (audio), etc.",
        key="bg_uploader"
    )
    
    if bg and (bg.name != st.session_state.bg_name or not os.path.exists(st.session_state.bg_path)):
        try:
            bg_path = save_file(bg)
            st.session_state.bg_path = bg_path
            st.session_state.bg_name = bg.name
            
            # Determine file type
            if is_video_file(bg_path):
                # Try to load as video first
                try:
                    clip = VideoFileClip(bg_path)
                    if clip.audio is not None:
                        bg_duration = float(clip.audio.duration)
                        # SET DEFAULT: Use full audio duration
                        st.session_state.a_trim = [0.0, bg_duration]
                        st.session_state.bg_dur = bg_duration
                        st.success(f"✅ Video with audio: {bg.name} ({bg_duration:.1f}s)")
                    else:
                        # Video without audio, try as audio file
                        clip.close()
                        try:
                            audio = AudioFileClip(bg_path)
                            bg_duration = float(audio.duration)
                            st.session_state.a_trim = [0.0, bg_duration]
                            st.session_state.bg_dur = bg_duration
                            st.success(f"✅ Audio: {bg.name} ({bg_duration:.1f}s)")
                            audio.close()
                        except:
                            st.error(f"❌ {bg.name} has no audio track")
                            bg = None
                    clip.close()
                except Exception as e:
                    st.error(f"❌ Cannot load video file: {e}")
                    bg = None
            
            elif is_audio_file(bg_path):
                try:
                    audio = AudioFileClip(bg_path)
                    bg_duration = float(audio.duration)
                    st.session_state.a_trim = [0.0, bg_duration]
                    st.session_state.bg_dur = bg_duration
                    st.success(f"✅ Audio: {bg.name} ({bg_duration:.1f}s)")
                    audio.close()
                except Exception as e:
                    st.error(f"❌ Cannot load audio file: {e}")
                    bg = None
            
            else:
                st.error(f"❌ Unsupported file type: {bg.name}")
                bg = None
                
            # Reset output video state when new files are uploaded
            st.session_state.output_video_created = False
            st.session_state.output_video_path = None
                
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
            bg = None
    elif bg:
        st.success(f"✅ Audio loaded: {st.session_state.bg_name} ({st.session_state.bg_dur:.1f}s)")

with c2:
    ov = st.file_uploader(
        "Upload video or image",
        type=["mp4", "mov", "avi", "mkv", "webm", "jpg", "jpeg", "png", "gif", "bmp", "webp"],
        help="Supported: Videos (MP4, MOV, AVI, etc.) and Images (JPG, PNG, GIF, etc.)",
        key="ov_uploader"
    )
    
    if ov and (ov.name != st.session_state.ov_name or not os.path.exists(st.session_state.ov_path)):
        try:
            ov_path = save_file(ov)
            st.session_state.ov_path = ov_path
            st.session_state.ov_name = ov.name
            
            if is_image_file(ov_path):
                st.session_state.is_img = True
                try:
                    img = Image.open(ov_path)
                    st.image(img, width=300)
                    st.success(f"✅ Image: {ov.name}")
                    # For images, set default duration to match audio duration
                    if st.session_state.bg_dur > 0:
                        st.session_state.img_dur = float(st.session_state.bg_dur)
                except Exception as e:
                    st.error(f"❌ Cannot load image: {e}")
                    ov = None
            else:
                st.session_state.is_img = False
                try:
                    ov_clip = VideoFileClip(ov_path, audio=False)
                    ov_duration = float(ov_clip.duration)
                    # SET DEFAULT: Use full video duration
                    st.session_state.v_trim = [0.0, ov_duration]
                    st.session_state.ov_dur = ov_duration
                    w, h = ov_clip.size
                    orientation = "Portrait" if h > w else "Landscape" if w > h else "Square"
                    st.success(f"✅ Video: {ov.name} ({ov_duration:.1f}s)")
                    st.info(f"📐 {w}×{h} ({orientation})")
                    ov_clip.close()
                except Exception as e:
                    st.error(f"❌ Cannot load video: {e}")
                    ov = None
            
            # Reset output video state when new files are uploaded
            st.session_state.output_video_created = False
            st.session_state.output_video_path = None
                    
        except Exception as e:
            st.error(f"❌ Error processing file: {e}")
            ov = None
    elif ov:
        if st.session_state.is_img:
            st.success(f"✅ Image loaded: {st.session_state.ov_name}")
        else:
            st.success(f"✅ Video loaded: {st.session_state.ov_name} ({st.session_state.ov_dur:.1f}s)")

# Audio trim - Allow full control
if bg and st.session_state.bg_dur > 0:
    st.subheader("Audio Selection")
    
    # Get actual duration
    actual_duration = float(st.session_state.bg_dur)
    
    # Create slider - allow user to trim as they wish
    a_trim = st.slider("Select audio segment", 
                      0.0, 
                      actual_duration, 
                      (0.0, actual_duration),  # Full range selected by default
                      0.1,  # Smaller step for precise trimming
                      format="%.1fs")
    
    # Ensure end is greater than start
    if a_trim[1] <= a_trim[0]:
        a_trim = (a_trim[0], min(a_trim[0] + 0.1, actual_duration))
    
    st.session_state.a_trim = list(a_trim)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(a_trim[0]))
    c2.metric("End", fmt_time(a_trim[1]))
    audio_duration = a_trim[1] - a_trim[0]
    c3.metric("Duration", fmt_time(audio_duration))
    
    # Auto-update image duration to match audio if it's an image
    if ov and st.session_state.is_img:
        st.session_state.img_dur = audio_duration

# Video overlay settings
if ov and not st.session_state.is_img and st.session_state.ov_dur > 0:
    st.subheader("Video Overlay Settings")
    
    # Get actual duration
    actual_duration = float(st.session_state.ov_dur)
    
    # Create slider for video trimming
    v_trim = st.slider("Select video segment", 
                      0.0, 
                      actual_duration, 
                      (0.0, actual_duration),  # Full range selected by default
                      0.1,  # Smaller step for precise trimming
                      format="%.1fs",
                      key="video_trim_slider")
    
    # Ensure end is greater than start
    if v_trim[1] <= v_trim[0]:
        v_trim = (v_trim[0], min(v_trim[0] + 0.1, actual_duration))
    
    st.session_state.v_trim = list(v_trim)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(v_trim[0]))
    c2.metric("End", fmt_time(v_trim[1]))
    video_segment_duration = v_trim[1] - v_trim[0]
    c3.metric("Duration", fmt_time(video_segment_duration))
    
    st.info(f"🎥 Video segment ({fmt_time(video_segment_duration)}) will be looped/trimmed to match audio duration: {fmt_time(audio_duration)}")

# Image overlay settings
elif ov and st.session_state.is_img and st.session_state.bg_dur > 0:
    st.subheader("Image Settings")
    
    # Get audio duration for max limit
    audio_duration = st.session_state.a_trim[1] - st.session_state.a_trim[0]
    
    # Set image duration to match audio by default
    if st.session_state.img_dur != audio_duration:
        st.session_state.img_dur = audio_duration
    
    # Allow user to adjust image duration (matches audio by default)
    img_dur = st.slider("Image display time", 
                        0.1,  # Minimum 0.1 seconds
                        max(30.0, audio_duration),  # Max of 30s or audio duration
                        float(audio_duration),  # Default to audio duration
                        0.1, 
                        format="%.1fs")
    
    st.session_state.img_dur = img_dur
    
    st.info(f"🖼️ Image will display for: {fmt_time(st.session_state.img_dur)}")

# Output format selection
if bg and ov:
    st.subheader("📐 Output Format")
    selected_preset = st.selectbox("Choose output dimensions", list(PRESETS.keys()), 
                                  index=list(PRESETS.keys()).index(st.session_state.selected_preset) 
                                  if st.session_state.selected_preset in PRESETS else 0)
    st.session_state.selected_preset = selected_preset
    target_dims = PRESETS[selected_preset]
    
    if target_dims:
        st.info(f"Will resize to: {target_dims[0]}×{target_dims[1]} (adds black bars to maintain aspect ratio)")
    else:
        st.info("Original dimensions will be preserved")

# ========== PROCESS VIDEO WHEN CREATE BUTTON IS CLICKED ==========
if create_btn and st.session_state.bg_path and st.session_state.ov_path:
    try:
        with st.spinner("Processing video..."):
            # Load background audio
            is_vid = is_video_file(st.session_state.bg_path)
            audio = None
            audio_src = None
            
            try:
                if is_vid:
                    audio_src = VideoFileClip(st.session_state.bg_path)
                    audio = audio_src.audio
                else:
                    audio_src = AudioFileClip(st.session_state.bg_path)
                    audio = audio_src
                
                if audio is None:
                    raise Exception("No audio track found in file")
                
                # Get the selected audio segment
                trim_start = st.session_state.a_trim[0]
                trim_end = st.session_state.a_trim[1]
                
                # Extract audio segment
                audio_segment = audio.subclip(trim_start, trim_end)
                audio_duration = audio_segment.duration
                
                st.info(f"🎵 Using audio: {fmt_time(audio_duration)}")
                
            except Exception as e:
                st.error(f"❌ Error loading audio: {e}")
                raise
            
            # Process overlay
            final = None
            ov_final = None
            
            if st.session_state.is_img:
                try:
                    # Load and process image
                    img = Image.open(st.session_state.ov_path)
                    img_arr = np.array(img)
                    
                    # Resize image if target dims specified
                    if target_dims:
                        img_arr = resize_frame(img_arr, target_dims)
                    
                    # Create image clip
                    img_duration = min(st.session_state.img_dur, audio_duration)
                    img_clip = ImageClip(img_arr, duration=img_duration)
                    
                    # If image duration is shorter than audio, create background
                    if img_duration < audio_duration:
                        bg_clip = ColorClip(size=img_clip.size, color=(0, 0, 0), duration=audio_duration)
                        ov_final = CompositeVideoClip([bg_clip, img_clip.set_position('center')], duration=audio_duration)
                    else:
                        ov_final = img_clip.set_duration(audio_duration)
                    
                    # Create final video
                    final = ov_final.set_audio(audio_segment)
                    
                except Exception as e:
                    st.error(f"❌ Error processing image: {e}")
                    raise
            else:
                try:
                    # Load video overlay
                    ov_clip = VideoFileClip(st.session_state.ov_path, audio=False)
                    
                    # Get selected video segment
                    v_trim_start = st.session_state.v_trim[0]
                    v_trim_end = st.session_state.v_trim[1]
                    
                    # Extract video segment
                    video_segment = ov_clip.subclip(v_trim_start, v_trim_end)
                    video_duration = video_segment.duration
                    
                    st.info(f"🎥 Using video segment: {fmt_time(video_duration)}")
                    
                    # Loop or trim video to match audio duration
                    if video_duration < audio_duration:
                        # Loop the video
                        loops_needed = int(np.ceil(audio_duration / video_duration))
                        ov_final = concatenate_videoclips([video_segment] * loops_needed)
                        ov_final = ov_final.subclip(0, audio_duration)
                        st.info(f"🔄 Looped video {loops_needed} times to match audio")
                    elif video_duration > audio_duration:
                        # Trim the video
                        ov_final = video_segment.subclip(0, audio_duration)
                        st.info("✂️ Trimmed video to match audio duration")
                    else:
                        # Durations match exactly
                        ov_final = video_segment
                    
                    # Apply resize if needed
                    if target_dims:
                        st.info("⏳ Resizing video...")
                        ov_final = apply_resize_to_clip(ov_final, target_dims)
                    
                    # Create final video
                    final = ov_final.set_audio(audio_segment)
                    
                    # Close the original clip
                    ov_clip.close()
                    video_segment.close()
                    
                except Exception as e:
                    st.error(f"❌ Error processing video: {e}")
                    raise
            
            # Save final video
            out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            # Write video file
            st.info("📹 Rendering video...")
            final.write_videofile(
                out, 
                fps=24 if st.session_state.is_img else 30,  # Lower FPS for images to reduce file size
                codec="libx264", 
                audio_codec="aac", 
                bitrate="5M", 
                verbose=False, 
                logger=None,
                preset='medium',
                threads=4
            )
        
        st.success("✅ Video created successfully!")
        
        # Display the video
        st.video(out)
        
        # Store video info for download button
        w, h = final.size
        format_name = st.session_state.selected_preset.split(" - ")[0].replace("📱 ", "").replace("📺 ", "").replace("⬜ ", "").replace(" ", "_")
        
        st.session_state.output_video_path = out
        st.session_state.output_video_created = True
        st.session_state.output_video_info = {
            'width': w,
            'height': h,
            'duration': audio_duration,
            'format_name': format_name,
            'file_size': os.path.getsize(out) / (1024 * 1024)
        }
        
        # Show video stats
        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{audio_duration:.1f}s")
        c2.metric("Resolution", f"{w}×{h}")
        c3.metric("Size", f"{st.session_state.output_video_info['file_size']:.1f}MB")
        
        # Update the download button at the top by triggering a rerun
        st.rerun()
        
        # Cleanup - only close at the very end
        try:
            if audio_segment:
                audio_segment.close()
            if audio_src:
                audio_src.close()
            if ov_final:
                ov_final.close()
            if final:
                final.close()
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# ========== BOTTOM BUTTONS (AS BACKUP) ==========
if not st.session_state.output_video_created:
    st.divider()
    create_disabled_bottom = not (st.session_state.bg_path and st.session_state.ov_path and 
                                os.path.exists(st.session_state.bg_path) and 
                                os.path.exists(st.session_state.ov_path))
    if st.button("🎬 Create Video", 
                type="primary", 
                disabled=create_disabled_bottom, 
                use_container_width=True,
                key="create_bottom"):
        # This will trigger the create logic above when clicked
        pass

# Cleanup old temporary files on rerun
if st.session_state.get('bg_path') and not os.path.exists(st.session_state.bg_path):
    st.session_state.bg_path = ''
    st.session_state.bg_name = ''
if st.session_state.get('ov_path') and not os.path.exists(st.session_state.ov_path):
    st.session_state.ov_path = ''
    st.session_state.ov_name = ''
