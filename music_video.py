import streamlit as st
import tempfile
import os
import gc
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Simple Video Combiner",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Hide sidebar completely
st.markdown("""
<style>
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Simple mobile-friendly buttons */
    .stButton > button {
        width: 100%;
        padding: 12px;
        font-size: 16px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title("🎬 Simple Video Combiner")
st.caption("Overlay audio on video - No resizing, keep original quality")

# ---------- SIMPLE SESSION STATE ----------
if 'bg_audio' not in st.session_state:
    st.session_state.bg_audio = None
if 'video_clip' not in st.session_state:
    st.session_state.video_clip = None
if 'bg_duration' not in st.session_state:
    st.session_state.bg_duration = 0
if 'video_duration' not in st.session_state:
    st.session_state.video_duration = 0

# ---------- UPLOAD SECTION ----------
st.subheader("1. Upload Files")

col1, col2 = st.columns(2)

with col1:
    audio_file = st.file_uploader(
        "Audio File",
        type=["mp3", "m4a", "wav", "mp4"],
        help="Upload audio file or video with audio"
    )

with col2:
    video_file = st.file_uploader(
        "Video File",
        type=["mp4", "mov"],
        help="Upload video file (will keep original size)"
    )

# ---------- PROCESS FILES ----------
def save_file(uploaded_file):
    """Simple file save function"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1])
    temp_file.write(uploaded_file.getvalue())
    temp_file.close()
    return temp_file.name

if audio_file and video_file:
    with st.spinner("Loading files..."):
        try:
            # Save and load audio
            audio_path = save_file(audio_file)
            if audio_file.name.lower().endswith(('.mp4', '.mov')):
                # Extract audio from video
                video_with_audio = VideoFileClip(audio_path)
                st.session_state.bg_audio = video_with_audio.audio
                video_with_audio.close()
            else:
                # Load pure audio file
                st.session_state.bg_audio = AudioFileClip(audio_path)
            
            st.session_state.bg_duration = st.session_state.bg_audio.duration
            
            # Save and load video (NO RESIZING)
            video_path = save_file(video_file)
            st.session_state.video_clip = VideoFileClip(video_path, audio=False)
            st.session_state.video_duration = st.session_state.video_clip.duration
            
            st.success(f"✅ Loaded both files!")
            st.info(f"Audio: {st.session_state.bg_duration:.1f}s | Video: {st.session_state.video_duration:.1f}s")
            
        except Exception as e:
            st.error(f"Error loading files: {str(e)}")

# ---------- SIMPLE PROCESSING ----------
def combine_video_simple():
    """Simple video+audio combination without any resizing"""
    try:
        # Use full audio duration
        audio_clip = st.session_state.bg_audio
        
        # Get video clip (original size, no changes)
        video_clip = st.session_state.video_clip
        
        # Handle different durations
        if video_clip.duration < audio_clip.duration:
            # Video is shorter - loop it
            loops_needed = int(audio_clip.duration // video_clip.duration) + 1
            video_segments = [video_clip] * loops_needed
            video_clip = video_segments[0]
            for segment in video_segments[1:]:
                video_clip = video_clip.append(segment, method="compose")
            video_clip = video_clip.subclip(0, audio_clip.duration)
        elif video_clip.duration > audio_clip.duration:
            # Video is longer - trim it
            video_clip = video_clip.subclip(0, audio_clip.duration)
        
        # Simply add audio to video (NO RESIZING, NO POSITIONING)
        final_video = video_clip.set_audio(audio_clip)
        final_duration = audio_clip.duration
        
        # Save with original video properties
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_combined.mp4").name
        
        # Get original video FPS
        original_fps = video_clip.fps if hasattr(video_clip, 'fps') and video_clip.fps else 30
        
        final_video.write_videofile(
            output_path,
            fps=original_fps,  # Keep original FPS
            codec="libx264",
            audio_codec="aac",
            bitrate="10M",  # Good quality
            verbose=False,
            logger=None,
            preset='medium',
            ffmpeg_params=['-movflags', '+faststart']
        )
        
        # Cleanup
        video_clip.close()
        final_video.close()
        
        return output_path, final_duration
        
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None, 0

# ---------- CREATE BUTTON ----------
st.divider()

if audio_file and video_file:
    if st.button("🎬 Combine Video & Audio", type="primary", use_container_width=True):
        with st.spinner("Combining video and audio..."):
            output_path, duration = combine_video_simple()
            
            if output_path and os.path.exists(output_path):
                st.success("✅ Video created!")
                
                # Show video info
                try:
                    clip = VideoFileClip(output_path, audio=False)
                    width, height = clip.size
                    clip.close()
                    
                    st.info(f"Output: {width}×{height} (original size) | Duration: {duration:.1f}s")
                except:
                    st.info(f"Duration: {duration:.1f}s")
                
                # Show video preview
                try:
                    st.video(output_path)
                except:
                    pass
                
                # Download button
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                with open(output_path, "rb") as f:
                    st.download_button(
                        "📥 Download Combined Video",
                        f,
                        file_name="combined_video.mp4",
                        mime="video/mp4",
                        type="primary",
                        use_container_width=True
                    )
                
                # Cleanup
                try:
                    os.unlink(output_path)
                except:
                    pass
                
                # Clear memory
                gc.collect()
else:
    st.info("👆 Please upload both an audio file and a video file")

# ---------- SIMPLE INSTRUCTIONS ----------
with st.expander("📖 How to Use", expanded=True):
    st.markdown("""
    ### Simple 3-Step Process:
    
    1. **Upload Audio** - MP3, M4A, or video with audio
    2. **Upload Video** - MP4 or MOV file (any size)
    3. **Click Combine** - Creates video with audio overlay
    
    ### What This Does:
    - **Keeps original video size** - No resizing!
    - **Matches audio to video length** - Loops or trims as needed
    - **Preserves quality** - No compression unless needed
    - **Simple output** - Ready-to-use video file
    
    ### For Best Results:
    - Use MP4 videos
    - Use MP3 or M4A audio
    - Keep files under 200MB
    - Videos will play at original dimensions
    """)

# ---------- FOOTER ----------
st.divider()
st.caption("Simple Video Combiner • No resizing • Keep original quality")
