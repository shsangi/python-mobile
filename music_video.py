import streamlit as st
import tempfile
import os
import gc
from PIL import Image

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips
)

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Video Trimmer",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    
    .stButton > button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- VERSION ----------
st.title("✂️ Video Trimmer")
st.caption("Trim audio and video to the same duration")

# ---------- SESSION STATE ----------
if 'bg_path' not in st.session_state:
    st.session_state.bg_path = None
if 'overlay_path' not in st.session_state:
    st.session_state.overlay_path = None
if 'bg_duration' not in st.session_state:
    st.session_state.bg_duration = 0
if 'overlay_duration' not in st.session_state:
    st.session_state.overlay_duration = 0
if 'bg_is_video' not in st.session_state:
    st.session_state.bg_is_video = False
if 'overlay_is_image' not in st.session_state:
    st.session_state.overlay_is_image = False

# ---------- HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

# ---------- UPLOAD SECTIONS ----------
st.subheader("Upload Files")

col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "Background Audio/Video",
        type=["mp3", "m4a", "mp4", "mov"],
        help="Audio or video file (audio will be used)"
    )
    
    if background_file:
        try:
            # Save file
            st.session_state.bg_path = save_uploaded_file(background_file)
            bg_ext = os.path.splitext(background_file.name)[1].lower()
            st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov']
            
            # Load to get duration
            if st.session_state.bg_is_video:
                clip = VideoFileClip(st.session_state.bg_path)
                audio = clip.audio
                if audio:
                    st.session_state.bg_duration = audio.duration
                    audio.close()
                else:
                    st.error("No audio found in video!")
                    st.stop()
                clip.close()
            else:
                audio = AudioFileClip(st.session_state.bg_path)
                st.session_state.bg_duration = audio.duration
                audio.close()
            
            st.success(f"✅ {background_file.name} ({st.session_state.bg_duration:.1f}s)")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

with col2:
    overlay_file = st.file_uploader(
        "Overlay Video",
        type=["mp4", "mov"],
        help="Video file (will be overlaid on audio)"
    )
    
    if overlay_file:
        try:
            # Save file
            st.session_state.overlay_path = save_uploaded_file(overlay_file)
            st.session_state.overlay_is_image = False
            
            # Load to get duration
            clip = VideoFileClip(st.session_state.overlay_path, audio=False)
            st.session_state.overlay_duration = clip.duration
            clip.close()
            
            st.success(f"✅ {overlay_file.name} ({st.session_state.overlay_duration:.1f}s)")
            
        except Exception as e:
            st.error(f"Error: {str(e)}")

# ---------- SIMPLE TRIM SLIDERS ----------
if st.session_state.bg_duration > 0 and st.session_state.overlay_duration > 0:
    st.subheader("Trim Settings")
    
    # Get minimum duration between audio and video
    min_duration = min(st.session_state.bg_duration, st.session_state.overlay_duration)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Audio Start Time**")
        audio_start = st.slider(
            "Audio Start (seconds)",
            0.0,
            st.session_state.bg_duration - 0.1,
            0.0,
            0.1,
            key="audio_start",
            label_visibility="collapsed"
        )
    
    with col2:
        st.markdown("**Video Start Time**")
        video_start = st.slider(
            "Video Start (seconds)",
            0.0,
            st.session_state.overlay_duration - 0.1,
            0.0,
            0.1,
            key="video_start",
            label_visibility="collapsed"
        )
    
    # Calculate max end based on start times
    audio_max_end = st.session_state.bg_duration
    video_max_end = st.session_state.overlay_duration
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**Audio Duration**")
        audio_duration = st.slider(
            "Audio Duration (seconds)",
            0.1,
            audio_max_end - audio_start,
            min(10.0, audio_max_end - audio_start),
            0.1,
            key="audio_duration",
            label_visibility="collapsed"
        )
    
    with col4:
        st.markdown("**Video Duration**")
        video_duration = st.slider(
            "Video Duration (seconds)",
            0.1,
            video_max_end - video_start,
            min(10.0, video_max_end - video_start),
            0.1,
            key="video_duration",
            label_visibility="collapsed"
        )
    
    # Show summary
    st.info(f"""
    **Summary:**
    - Audio: From {audio_start:.1f}s for {audio_duration:.1f}s
    - Video: From {video_start:.1f}s for {video_duration:.1f}s
    """)

# ---------- SIMPLE PROCESS FUNCTION ----------
def trim_and_combine():
    """Simply trim audio and video, then combine (no resizing)"""
    try:
        # Get trim settings
        audio_start = st.session_state.get('audio_start', 0)
        audio_duration = st.session_state.get('audio_duration', 10)
        audio_end = audio_start + audio_duration
        
        video_start = st.session_state.get('video_start', 0)
        video_duration = st.session_state.get('video_duration', 10)
        video_end = video_start + video_duration
        
        # Use shorter duration
        final_duration = min(audio_duration, video_duration)
        
        # Load and trim audio
        if st.session_state.bg_is_video:
            bg_clip = VideoFileClip(st.session_state.bg_path)
            audio_clip = bg_clip.audio.subclip(audio_start, audio_start + final_duration)
            bg_clip.close()
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_start + final_duration)
        
        # Load and trim video
        video_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
        
        # Check if video needs to be looped
        if video_duration < final_duration:
            # Loop video if it's shorter than needed
            loops_needed = int(final_duration / video_duration) + 1
            video_segments = []
            
            for i in range(loops_needed):
                segment = video_clip.subclip(video_start, min(video_end, video_clip.duration))
                video_segments.append(segment)
            
            video_clip_final = concatenate_videoclips(video_segments)
            video_clip_final = video_clip_final.subclip(0, final_duration)
            video_clip.close()
        else:
            # Just trim the video
            video_clip_final = video_clip.subclip(video_start, video_start + final_duration)
            video_clip.close()
        
        # Add audio to video
        final_video = video_clip_final.set_audio(audio_clip)
        final_video = final_video.set_duration(final_duration)
        
        # Save video
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        
        final_video.write_videofile(
            output_path,
            fps=video_clip_final.fps if hasattr(video_clip_final, 'fps') else 30,
            codec="libx264",
            audio_codec="aac",
            bitrate="5M",
            verbose=False,
            logger=None,
            preset='fast'
        )
        
        # Cleanup
        audio_clip.close()
        video_clip_final.close()
        final_video.close()
        
        return output_path, final_duration
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        import traceback
        with st.expander("Details"):
            st.code(traceback.format_exc())
        return None, 0

# ---------- CREATE BUTTON ----------
st.divider()

if st.session_state.bg_path and st.session_state.overlay_path:
    if st.button("🎬 Create Combined Video", type="primary", use_container_width=True):
        with st.spinner("Processing..."):
            output_path, duration = trim_and_combine()
            
            if output_path and os.path.exists(output_path):
                st.success("✅ Video created!")
                
                # Show video
                st.video(output_path)
                
                # Show info
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Duration", f"{duration:.1f}s")
                with col2:
                    st.metric("File Size", f"{file_size:.1f}MB")
                
                # Download button
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Video",
                        f,
                        file_name="trimmed_video.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
                
                # Cleanup temp files
                try:
                    if st.session_state.bg_path:
                        os.unlink(st.session_state.bg_path)
                    if st.session_state.overlay_path:
                        os.unlink(st.session_state.overlay_path)
                except:
                    pass
                
                # Clear session state
                keys_to_clear = ['bg_path', 'overlay_path', 'bg_duration', 'overlay_duration']
                for key in keys_to_clear:
                    if key in st.session_state:
                        st.session_state[key] = None
                
                gc.collect()
else:
    st.info("Please upload both an audio/video file and a video overlay to begin")

# ---------- SIMPLE INSTRUCTIONS ----------
with st.expander("How to Use", expanded=True):
    st.markdown("""
    ### Simple Video Trimmer
    
    1. **Upload Files**:
       - **Audio/Video**: Any file with audio (MP3, MP4, etc.)
       - **Video Overlay**: Any video file (MP4, MOV)
    
    2. **Trim Settings**:
       - Set **start time** for audio
       - Set **start time** for video
       - Set **duration** for both
    
    3. **Create Video**:
       - Video and audio will be trimmed to your settings
       - If video is shorter than audio, it will loop
       - No resizing - keeps original video dimensions
    
    **Note**: The final video will use the shorter duration between your audio and video settings.
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Simple Video Trimmer • No resizing • Just trimming")
