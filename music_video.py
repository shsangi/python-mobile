import streamlit as st
import tempfile
import os
from PIL import Image
import numpy as np
import subprocess
import json
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip
from moviepy.video.VideoClip import ColorClip

st.set_page_config(page_title="🎬 Mobile Video Maker", layout="centered")
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
for k, v in {'bg_dur': 0.0, 'ov_dur': 0.0, 'a_trim': [0.0, 30.0], 'v_trim': [0.0, 30.0], 'img_dur': 5.0, 'rotation': 0, 'output_path': None}.items():
    st.session_state.setdefault(k, v)

def save_file(f):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1])
    tmp.write(f.getvalue())
    tmp.close()
    return tmp.name

def fmt_time(s):
    return f"{int(s//60):02d}:{int(s%60):02d}" if s < 3600 else f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"

def get_video_rotation(video_path):
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
               '-show_entries', 'stream_tags=rotate', '-of', 'json', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        return int(data['streams'][0].get('tags', {}).get('rotate', 0))
    except:
        return 0

def resize_video_to_fit(clip, target_size):
    """Resize video to fit target dimensions while maintaining aspect ratio with black bars"""
    target_w, target_h = target_size
    clip_w, clip_h = clip.size
    
    # Calculate scaling
    scale = min(target_w / clip_w, target_h / clip_h)
    new_w, new_h = int(clip_w * scale), int(clip_h * scale)
    
    # Make dimensions even (required for video encoding)
    new_w = new_w if new_w % 2 == 0 else new_w - 1
    new_h = new_h if new_h % 2 == 0 else new_h - 1
    
    # Resize clip using newsize parameter
    resized = clip.resize(newsize=(new_w, new_h))
    
    # Create black background
    bg = ColorClip(size=target_size, color=(0, 0, 0), duration=clip.duration)
    
    # Center the resized clip
    x_pos = (target_w - new_w) // 2
    y_pos = (target_h - new_h) // 2
    
    return CompositeVideoClip([bg, resized.set_position((x_pos, y_pos))], size=target_size)

# Upload section
c1, c2 = st.columns(2)

with c1:
    bg = st.file_uploader("Background Audio/Video", type=["mp3", "mp4", "mov", "m4a"])
    if bg:
        bg_path = save_file(bg)
        is_vid = bg.name.endswith(('.mp4', '.mov'))
        clip = VideoFileClip(bg_path) if is_vid else None
        audio = clip.audio if is_vid else AudioFileClip(bg_path)
        st.session_state.bg_dur = float(audio.duration)
        st.session_state.a_trim = [0.0, min(30.0, float(audio.duration))]
        st.success(f"✅ {bg.name} ({audio.duration:.1f}s)")
        
with c2:
    ov = st.file_uploader("Overlay (Video/Image)", type=["mp4", "mov", "jpg", "jpeg", "png", "gif"])
    if ov:
        ov_path = save_file(ov)
        is_img = ov.name.endswith(('.jpg', '.jpeg', '.png', '.gif'))
        if is_img:
            img = Image.open(ov_path)
            st.image(img, width=300)
            st.success(f"✅ Image: {ov.name}")
        else:
            rotation = get_video_rotation(ov_path)
            st.session_state.rotation = rotation
            ov_clip = VideoFileClip(ov_path, audio=False)
            st.session_state.ov_dur = float(ov_clip.duration)
            st.session_state.v_trim = [0.0, min(30.0, float(ov_clip.duration))]
            w, h = ov_clip.size
            
            if rotation in [90, 270]:
                display_w, display_h = h, w
                orientation = "Portrait (rotated)"
            else:
                display_w, display_h = w, h
                orientation = "Portrait" if display_h > display_w else "Landscape" if display_w > display_h else "Square"
            
            st.success(f"✅ Video: {ov.name} ({ov_clip.duration:.1f}s)")
            st.info(f"📐 {display_w}×{display_h} ({orientation})")
            if rotation != 0:
                st.warning(f"🔄 Rotation: {rotation}° - will be corrected!")

# Audio trim
if st.session_state.bg_dur > 0:
    st.subheader("Audio Selection")
    a_trim = st.slider("Audio range", 0.0, float(st.session_state.bg_dur), tuple(map(float, st.session_state.a_trim)), 0.5, format="%.1fs")
    st.session_state.a_trim = list(a_trim)
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(a_trim[0]))
    c2.metric("End", fmt_time(a_trim[1]))
    c3.metric("Duration", fmt_time(a_trim[1] - a_trim[0]))

# Video/Image overlay settings
if ov and not is_img and st.session_state.ov_dur > 0:
    st.subheader("Video Overlay")
    v_trim = st.slider("Video range", 0.0, float(st.session_state.ov_dur), tuple(map(float, st.session_state.v_trim)), 0.5, format="%.1fs")
    st.session_state.v_trim = list(v_trim)
    c1, c2, c3 = st.columns(3)
    c1.metric("Start", fmt_time(v_trim[0]))
    c2.metric("End", fmt_time(v_trim[1]))
    c3.metric("Duration", fmt_time(v_trim[1] - v_trim[0]))
elif ov and is_img and st.session_state.bg_dur > 0:
    st.subheader("Image Duration")
    max_dur = st.session_state.a_trim[1] - st.session_state.a_trim[0]
    st.session_state.img_dur = st.slider("Display time", 1.0, float(max_dur), min(30.0, float(max_dur)), 0.5, format="%.1fs")

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
            st.write("🔄 Step 1: Extracting audio...")
            # Extract audio
            audio_src = clip if is_vid else AudioFileClip(bg_path)
            audio = audio_src.audio.subclip(*st.session_state.a_trim) if is_vid else audio_src.subclip(*st.session_state.a_trim)
            dur = audio.duration
            st.write(f"✅ Audio extracted: {dur:.1f}s")
            
            # Process overlay
            st.write("🔄 Step 2: Processing overlay...")
            if is_img:
                img_arr = np.array(img)
                img_dur = min(st.session_state.img_dur, dur)
                ov_final = ImageClip(img_arr, duration=img_dur)
                if img_dur < dur:
                    bg_clip = ColorClip(size=ov_final.size, color=(0,0,0), duration=dur)
                    ov_final = CompositeVideoClip([bg_clip, ov_final.set_position('center')], duration=dur)
                st.write(f"✅ Image overlay ready: {ov_final.size}")
            else:
                ov_final = ov_clip.subclip(*st.session_state.v_trim)
                st.write(f"✅ Video trimmed: {ov_final.size}")
                
                # Apply rotation if needed
                rotation = st.session_state.rotation
                if rotation != 0:
                    st.write(f"🔄 Applying rotation: {rotation}°...")
                    if rotation == 90:
                        ov_final = ov_final.rotate(-90)
                    elif rotation == 270:
                        ov_final = ov_final.rotate(90)
                    elif rotation == 180:
                        ov_final = ov_final.rotate(180)
                    st.write(f"✅ Rotation applied: {ov_final.size}")
                
                if ov_final.duration < dur:
                    st.write("🔄 Looping video to match audio...")
                    loops = int(dur / ov_final.duration) + 1
                    ov_final = concatenate_videoclips([ov_final] * loops).subclip(0, dur)
                elif ov_final.duration > dur:
                    ov_final = ov_final.subclip(0, dur)
                st.write(f"✅ Duration matched: {ov_final.duration:.1f}s")
            
            # Apply target dimensions if selected
            if target_dims:
                st.write(f"🔄 Step 3: Resizing to {target_dims[0]}×{target_dims[1]}...")
                st.write(f"Original size: {ov_final.size}")
                
                target_w, target_h = target_dims
                clip_w, clip_h = ov_final.size
                
                # Calculate scaling
                scale = min(target_w / clip_w, target_h / clip_h)
                new_w, new_h = int(clip_w * scale), int(clip_h * scale)
                
                # Make dimensions even
                new_w = new_w if new_w % 2 == 0 else new_w - 1
                new_h = new_h if new_h % 2 == 0 else new_h - 1
                
                st.write(f"Calculated new size: {new_w}×{new_h}")
                st.write(f"Resizing clip...")
                
                try:
                    # Try method 1: using newsize
                    resized = ov_final.resize(newsize=(new_w, new_h))
                    st.write("✅ Resize successful (method 1)")
                except Exception as e1:
                    st.write(f"⚠️ Method 1 failed: {e1}")
                    try:
                        # Try method 2: using width/height
                        resized = ov_final.resize(width=new_w, height=new_h)
                        st.write("✅ Resize successful (method 2)")
                    except Exception as e2:
                        st.write(f"⚠️ Method 2 failed: {e2}")
                        # Try method 3: using fx
                        from moviepy.video.fx.resize import resize as fx_resize
                        resized = fx_resize(ov_final, newsize=(new_w, new_h))
                        st.write("✅ Resize successful (method 3)")
                
                st.write("🔄 Creating black background...")
                bg_clip = ColorClip(size=target_dims, color=(0, 0, 0), duration=ov_final.duration)
                
                st.write("🔄 Compositing video...")
                x_pos = (target_w - new_w) // 2
                y_pos = (target_h - new_h) // 2
                ov_final = CompositeVideoClip([bg_clip, resized.set_position((x_pos, y_pos))], size=target_dims)
                st.write(f"✅ Resize complete: {ov_final.size}")
            
            st.write("🔄 Step 4: Adding audio...")
            final = ov_final.set_audio(audio).set_duration(dur)
            
            st.write("🔄 Step 5: Rendering video...")
            out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
            
            ffmpeg_params = ['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2']
            if not is_img and st.session_state.rotation != 0:
                ffmpeg_params.extend(['-metadata:s:v:0', 'rotate=0'])
            
            final.write_videofile(
                out, 
                fps=30,
                codec="libx264", 
                audio_codec="aac", 
                bitrate="8M", 
                verbose=False, 
                logger=None,
                preset='medium',
                ffmpeg_params=ffmpeg_params
            )
            
            st.session_state.output_path = out
        
        st.success("✅ Video created successfully!")
        st.video(out)
        
        w, h = final.size
        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{dur:.1f}s")
        c2.metric("Resolution", f"{w}×{h}")
        c3.metric("Size", f"{os.path.getsize(out)/(1024*1024):.1f}MB")
        
        # Format name for download
        format_name = selected_preset.split(" - ")[0].replace("📱 ", "").replace("📺 ", "").replace("⬜ ", "").replace(" ", "_")
        
        with open(out, "rb") as f:
            st.download_button("📥 Download Video", f, f"{format_name}_{w}x{h}.mp4", "video/mp4", type="primary", use_container_width=True)
        
        # Cleanup
        audio.close()
        if not is_img:
            ov_clip.close()
        if is_vid:
            clip.close()
        else:
            audio_src.close()
        ov_final.close()
        final.close()
        
        import time
        time.sleep(0.5)
        
        try:
            os.unlink(bg_path)
            os.unlink(ov_path)
        except:
            pass
        
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())
