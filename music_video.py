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
st.caption("Combine audio with video - Auto-detects mobile video rotation")

# Initialize session state
for k, v in {'bg_dur': 0.0, 'ov_dur': 0.0, 'a_trim': [0.0, 30.0], 'v_trim': [0.0, 30.0], 'img_dur': 5.0, 'rotation': 0}.items():
    st.session_state.setdefault(k, v)

def save_file(f):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1])
    tmp.write(f.getvalue())
    tmp.close()
    return tmp.name

def fmt_time(s):
    return f"{int(s//60):02d}:{int(s%60):02d}" if s < 3600 else f"{int(s//3600):02d}:{int((s%3600)//60):02d}:{int(s%60):02d}"

def get_video_rotation(video_path):
    """Get rotation metadata from video using ffprobe"""
    try:
        cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', 
               '-show_entries', 'stream_tags=rotate', '-of', 'json', video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)
        rotation = int(data['streams'][0].get('tags', {}).get('rotate', 0))
        return rotation
    except:
        return 0

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
            # Get rotation BEFORE loading with MoviePy
            rotation = get_video_rotation(ov_path)
            st.session_state.rotation = rotation
            
            ov_clip = VideoFileClip(ov_path, audio=False)
            st.session_state.ov_dur = float(ov_clip.duration)
            st.session_state.v_trim = [0.0, min(30.0, float(ov_clip.duration))]
            w, h = ov_clip.size
            
            # Adjust display based on rotation
            if rotation in [90, 270]:
                display_w, display_h = h, w  # Swapped for rotated video
                orientation = "Portrait (rotated)" if display_h > display_w else "Landscape (rotated)"
            else:
                display_w, display_h = w, h
                orientation = "Portrait" if display_h > display_w else "Landscape" if display_w > display_h else "Square"
            
            st.success(f"✅ Video: {ov.name} ({ov_clip.duration:.1f}s)")
            st.info(f"📐 {display_w}×{display_h} ({orientation})")
            if rotation != 0:
                st.warning(f"🔄 Rotation detected: {rotation}° - will be corrected!")

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

# Process button
st.divider()
if st.button("🎬 Create Video", type="primary", disabled=not (bg and ov), use_container_width=True):
    try:
        # Extract audio
        audio_src = clip if is_vid else AudioFileClip(bg_path)
        audio = audio_src.audio.subclip(*st.session_state.a_trim) if is_vid else audio_src.subclip(*st.session_state.a_trim)
        dur = audio.duration
        
        # Process overlay
        if is_img:
            img_arr = np.array(img)
            img_dur = min(st.session_state.img_dur, dur)
            ov_final = ImageClip(img_arr, duration=img_dur)
            if img_dur < dur:
                bg_clip = ColorClip(size=ov_final.size, color=(0,0,0), duration=dur)
                ov_final = CompositeVideoClip([bg_clip, ov_final.set_position('center')], duration=dur)
        else:
            ov_final = ov_clip.subclip(*st.session_state.v_trim)
            
            # Apply rotation if needed
            rotation = st.session_state.rotation
            if rotation == 90:
                ov_final = ov_final.rotate(-90)
            elif rotation == 270:
                ov_final = ov_final.rotate(90)
            elif rotation == 180:
                ov_final = ov_final.rotate(180)
            
            if ov_final.duration < dur:
                loops = int(dur / ov_final.duration) + 1
                ov_final = concatenate_videoclips([ov_final] * loops).subclip(0, dur)
            elif ov_final.duration > dur:
                ov_final = ov_final.subclip(0, dur)
        
        final = ov_final.set_audio(audio).set_duration(dur)
        out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        
        # Build ffmpeg params based on rotation
        ffmpeg_params = ['-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2']
        if not is_img and st.session_state.rotation != 0:
            # Remove rotation metadata from output
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
        
        st.success("✅ Video created!")
        st.video(out)
        
        w, h = final.size
        c1, c2, c3 = st.columns(3)
        c1.metric("Duration", f"{dur:.1f}s")
        c2.metric("Resolution", f"{w}×{h}")
        c3.metric("Size", f"{os.path.getsize(out)/(1024*1024):.1f}MB")
        
        with open(out, "rb") as f:
            st.download_button("📥 Download", f, f"video_{w}x{h}.mp4", "video/mp4", type="primary", use_container_width=True)
        
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
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())
