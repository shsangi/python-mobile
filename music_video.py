import streamlit as st
import tempfile
import os
import gc
from PIL import Image
import base64
import time

import moviepy
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    concatenate_videoclips
)

# ---------- VERSION ----------
APP_VERSION = "21.1"  # Update with each change
my_title = f"🎬 Mobile Video Maker V {APP_VERSION}"

# ---------- PAGE CONFIG (MOBILE OPTIMIZED) ----------
st.set_page_config(
    page_title=my_title,
    layout="wide",  # Changed to wide for better mobile control
    initial_sidebar_state="collapsed",
    menu_items=None
)

# ---------- MOBILE-FRIENDLY CSS ----------
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Mobile-responsive container */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100% !important;
    }
    
    /* Mobile-friendly buttons */
    .stButton > button {
        width: 100%;
        min-height: 3rem;
        font-size: 1.1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    
    /* Mobile-friendly sliders */
    .stSlider > div {
        padding: 0.5rem 0;
    }
    
    /* Mobile upload buttons */
    .stFileUploader > div > button {
        min-height: 2.5rem;
        width: 100%;
    }
    
    /* Mobile column adjustments */
    @media (max-width: 768px) {
        .stColumn {
            padding: 0.25rem !important;
        }
        
        h1 {
            font-size: 1.8rem !important;
        }
        
        h2 {
            font-size: 1.4rem !important;
        }
        
        h3 {
            font-size: 1.2rem !important;
        }
        
        /* Prevent horizontal scrolling */
        .element-container {
            overflow-x: hidden !important;
        }
        
        /* Mobile video preview */
        .stVideo {
            width: 100% !important;
            height: auto !important;
        }
        
        /* Metric cards for mobile */
        .stMetric {
            padding: 0.5rem !important;
        }
    }
    
    /* Touch-friendly elements */
    .stSlider > div > div > div {
        height: 1.5rem !important;
    }
    
    /* Mobile file uploader text */
    .stFileUploader > div > label {
        font-size: 0.9rem !important;
    }
    
    /* Prevent zoom on input focus for iOS */
    @media screen and (max-width: 768px) {
        input, select, textarea {
            font-size: 16px !important;
        }
    }
    
    /* Loading spinner adjustments */
    .stSpinner > div {
        margin: 1rem auto;
    }
    
    /* Mobile expander */
    .streamlit-expanderHeader {
        font-size: 1rem !important;
        padding: 0.75rem !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------- APP TITLE ----------
st.title(my_title)
st.caption("Trim audio and overlay videos - No resizing - Mobile Optimized")

# ---------- MOBILE DETECTION & WARNINGS ----------
def check_mobile_issues():
    """Check for common mobile browser issues"""
    warning_messages = []
    
    # Check if on mobile (simplified detection)
    user_agent = st.experimental_get_query_params().get('agent', [''])[0]
    is_mobile = 'mobi' in user_agent.lower() or any(x in user_agent.lower() 
                                                   for x in ['iphone', 'android', 'mobile'])
    
    if is_mobile:
        warning_messages.append("📱 **Mobile Browser Detected**")
        warning_messages.append("- Use landscape mode for better video preview")
        warning_messages.append("- Large files may take longer to process")
        warning_messages.append("- Ensure stable internet connection")
    
    return warning_messages

# ---------- SESSION STATE WITH MOBILE OPTIMIZATIONS ----------
session_defaults = {
    'bg_clip': None,
    'overlay_clip': None,
    'bg_duration': 0,
    'overlay_duration': 0,
    'bg_path': None,
    'overlay_path': None,
    'bg_is_video': False,
    'overlay_is_image': False,
    'prev_bg_file': None,
    'prev_overlay_file': None,
    'mobile_warnings_shown': False,
    'processing': False,
    'last_output_path': None,
    'mobile_orientation': 'portrait'
}

for key, value in session_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------- MOBILE-OPTIMIZED HELPER FUNCTIONS ----------
def save_uploaded_file(uploaded_file):
    """Save uploaded file to temp location with mobile optimizations"""
    try:
        # Check file size for mobile limitations
        file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
        if file_size_mb > 100:  # 100MB limit for mobile
            st.warning(f"⚠️ Large file ({file_size_mb:.1f}MB). Processing may be slow on mobile.")
        
        temp_file = tempfile.NamedTemporaryFile(
            delete=False, 
            suffix=os.path.splitext(uploaded_file.name)[1]
        )
        temp_file.write(uploaded_file.getvalue())
        temp_file.close()
        return temp_file.name
    except Exception as e:
        st.error(f"File save error: {str(e)}")
        return None

def show_single_frame_preview(video_path, time_point=1, mobile_optimized=True):
    """Show a single frame from video, optimized for mobile"""
    try:
        clip = VideoFileClip(video_path, audio=False)
        if time_point > clip.duration:
            time_point = clip.duration / 2
        
        frame = clip.get_frame(time_point)
        img = Image.fromarray(frame)
        
        # Mobile-optimized thumbnail size
        if mobile_optimized:
            max_size = (400, 400)  # Smaller for mobile
        else:
            max_size = (600, 600)
        
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        clip.close()
        return img
    except Exception as e:
        st.error(f"Preview error: {str(e)}")
        return None

def cleanup_temp_files():
    """Clean up temporary files to free memory (important for mobile)"""
    files_to_clean = [
        st.session_state.bg_path,
        st.session_state.overlay_path,
        st.session_state.last_output_path
    ]
    
    for file_path in files_to_clean:
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
            except:
                pass
    
    # Force garbage collection
    gc.collect()

# ---------- MOBILE WARNINGS ----------
mobile_warnings = check_mobile_issues()
if mobile_warnings and not st.session_state.mobile_warnings_shown:
    with st.expander("📱 Mobile Tips & Warnings", expanded=True):
        for warning in mobile_warnings:
            st.markdown(warning)
        st.markdown("---")
        st.markdown("**For best results:**")
        st.markdown("1. Use WiFi connection")
        st.markdown("2. Keep screen active during processing")
        st.markdown("3. Close other browser tabs")
        st.markdown("4. Use files under 50MB for faster processing")
    st.session_state.mobile_warnings_shown = True

# ---------- UPLOAD SECTIONS (MOBILE OPTIMIZED) ----------
st.subheader("📤 Upload Files")

# Mobile: Use single column layout for small screens
col1, col2 = st.columns(2)

with col1:
    background_file = st.file_uploader(
        "**Background Audio/Video**",
        type=["mp3", "mp4", "mov", "m4a", "wav", "avi"],
        help="Audio will be extracted. Max 200MB recommended for mobile.",
        key="bg_uploader"
    )
    
    if background_file:
        if st.session_state.prev_bg_file != background_file.name:
            st.session_state.bg_clip = None
            st.session_state.prev_bg_file = background_file.name
        
        # Show file info
        file_size = len(background_file.getvalue()) / (1024 * 1024)
        st.caption(f"Size: {file_size:.1f}MB • Type: {background_file.type}")
        
        # Save and load with progress
        with st.spinner("Loading background file..."):
            bg_path = save_uploaded_file(background_file)
            if bg_path:
                st.session_state.bg_path = bg_path
                bg_ext = os.path.splitext(background_file.name)[1].lower()
                st.session_state.bg_is_video = bg_ext in ['.mp4', '.mov', '.avi']
                
                try:
                    if st.session_state.bg_is_video:
                        st.session_state.bg_clip = VideoFileClip(st.session_state.bg_path)
                        audio = st.session_state.bg_clip.audio
                        if audio:
                            st.session_state.bg_duration = audio.duration
                            st.success(f"✅ Video loaded: {st.session_state.bg_duration:.1f}s")
                            
                            # Show quick video info for mobile
                            with st.expander("Video Info", expanded=False):
                                st.write(f"Dimensions: {st.session_state.bg_clip.size}")
                                st.write(f"FPS: {st.session_state.bg_clip.fps}")
                        else:
                            st.error("No audio in video file")
                    else:
                        audio = AudioFileClip(st.session_state.bg_path)
                        st.session_state.bg_duration = audio.duration
                        audio.close()
                        st.success(f"✅ Audio loaded: {st.session_state.bg_duration:.1f}s")
                        
                except Exception as e:
                    st.error(f"❌ Error loading file: {str(e)}")
                    if "memory" in str(e).lower():
                        st.info("Try a smaller file or close other apps")

with col2:
    overlay_file = st.file_uploader(
        "**Overlay Video**",
        type=["mp4", "mov", "avi", "mkv"],
        help="Video overlay (no resizing). Max 150MB for mobile.",
        key="overlay_uploader"
    )
    
    if overlay_file:
        if st.session_state.prev_overlay_file != overlay_file.name:
            st.session_state.overlay_clip = None
            st.session_state.prev_overlay_file = overlay_file.name
        
        # Show file info
        file_size = len(overlay_file.getvalue()) / (1024 * 1024)
        st.caption(f"Size: {file_size:.1f}MB • Type: {overlay_file.type}")
        
        # Save and load
        with st.spinner("Loading overlay video..."):
            overlay_path = save_uploaded_file(overlay_file)
            if overlay_path:
                st.session_state.overlay_path = overlay_path
                st.session_state.overlay_is_image = False
                
                try:
                    st.session_state.overlay_clip = VideoFileClip(st.session_state.overlay_path, audio=False)
                    st.session_state.overlay_duration = st.session_state.overlay_clip.duration
                    st.success(f"✅ Overlay loaded: {st.session_state.overlay_duration:.1f}s")
                    
                    # Mobile-optimized preview
                    with st.expander("Preview & Info", expanded=False):
                        preview_img = show_single_frame_preview(st.session_state.overlay_path, mobile_optimized=True)
                        if preview_img:
                            st.image(preview_img, caption="Frame preview", use_column_width=True)
                        
                        col_info1, col_info2 = st.columns(2)
                        with col_info1:
                            st.metric("Dimensions", f"{st.session_state.overlay_clip.size[0]}×{st.session_state.overlay_clip.size[1]}")
                        with col_info2:
                            st.metric("FPS", f"{st.session_state.overlay_clip.fps:.1f}")
                            
                except Exception as e:
                    st.error(f"❌ Error loading overlay: {str(e)}")

# ---------- MOBILE-FRIENDLY TRIM INTERFACE ----------
if st.session_state.bg_duration > 0 or st.session_state.overlay_duration > 0:
    st.subheader("✂️ Trim Settings")
    
    # Audio trim section
    if st.session_state.bg_duration > 0:
        with st.expander("Audio Trim", expanded=True):
            col_a1, col_a2, col_a3 = st.columns([2, 1, 1])
            
            with col_a1:
                audio_start = st.slider(
                    "Start (seconds)",
                    0.0,
                    float(st.session_state.bg_duration),
                    0.0,
                    0.5,
                    key="audio_start_mobile",
                    help="Audio start time"
                )
            
            max_audio_duration = st.session_state.bg_duration - audio_start
            
            with col_a2:
                default_duration = min(30.0, float(max_audio_duration))
                audio_duration = st.number_input(
                    "Duration (s)",
                    min_value=1.0,
                    max_value=float(max_audio_duration),
                    value=default_duration,
                    step=0.5,
                    key="audio_duration_mobile"
                )
            
            with col_a3:
                audio_end = audio_start + audio_duration
                st.metric("End", f"{audio_end:.1f}s")
            
            # Visual timeline for mobile
            st.progress(min(1.0, audio_end / st.session_state.bg_duration))
            st.caption(f"Audio: {audio_start:.1f}s → {audio_end:.1f}s ({audio_duration:.1f}s total)")

    # Video trim section
    if st.session_state.overlay_duration > 0:
        with st.expander("Video Trim", expanded=True):
            col_v1, col_v2, col_v3 = st.columns([2, 1, 1])
            
            with col_v1:
                overlay_start = st.slider(
                    "Start (seconds)",
                    0.0,
                    float(st.session_state.overlay_duration),
                    0.0,
                    0.5,
                    key="overlay_start_mobile",
                    help="Video start time"
                )
            
            max_overlay_duration = st.session_state.overlay_duration - overlay_start
            
            with col_v2:
                default_duration = min(30.0, float(max_overlay_duration))
                overlay_duration = st.number_input(
                    "Duration (s)",
                    min_value=1.0,
                    max_value=float(max_overlay_duration),
                    value=default_duration,
                    step=0.5,
                    key="overlay_duration_mobile"
                )
            
            with col_v3:
                overlay_end = overlay_start + overlay_duration
                st.metric("End", f"{overlay_end:.1f}s")
            
            # Visual timeline for mobile
            st.progress(min(1.0, overlay_end / st.session_state.overlay_duration))
            st.caption(f"Video: {overlay_start:.1f}s → {overlay_end:.1f}s ({overlay_duration:.1f}s total)")

# ---------- MOBILE-OPTIMIZED PROCESS FUNCTION ----------
def process_video_mobile():
    """Combine audio and video optimized for mobile processing"""
    try:
        st.session_state.processing = True
        
        # Get trim values from mobile-friendly controls
        audio_start = st.session_state.get('audio_start_mobile', 
                                         st.session_state.get('audio_start', 0))
        audio_duration_val = st.session_state.get('audio_duration_mobile',
                                                st.session_state.get('audio_duration', 30))
        audio_end = audio_start + audio_duration_val
        
        overlay_start = st.session_state.get('overlay_start_mobile',
                                           st.session_state.get('overlay_start', 0))
        overlay_duration_val = st.session_state.get('overlay_duration_mobile',
                                                  st.session_state.get('overlay_duration', 30))
        overlay_end = overlay_start + overlay_duration_val
        
        # Progress tracking for mobile
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Step 1: Extract audio
        status_text.text("Step 1/4: Extracting audio...")
        progress_bar.progress(25)
        
        if st.session_state.bg_is_video:
            audio_clip = st.session_state.bg_clip.audio.subclip(audio_start, audio_end)
        else:
            audio_clip = AudioFileClip(st.session_state.bg_path).subclip(audio_start, audio_end)
        
        final_audio_duration = audio_clip.duration
        
        # Step 2: Process overlay video
        status_text.text("Step 2/4: Processing video...")
        progress_bar.progress(50)
        
        overlay = st.session_state.overlay_clip.subclip(overlay_start, overlay_end)
        
        # Match durations for mobile - efficient looping
        if overlay.duration < final_audio_duration:
            loops_needed = int(final_audio_duration / overlay.duration) + 1
            # Use list comprehension for efficiency
            overlay_loops = [overlay] * loops_needed
            overlay = concatenate_videoclips(overlay_loops, method="compose")
            overlay = overlay.subclip(0, final_audio_duration)
        elif overlay.duration > final_audio_duration:
            overlay = overlay.subclip(0, final_audio_duration)
        
        # Step 3: Combine with audio
        status_text.text("Step 3/4: Combining audio and video...")
        progress_bar.progress(75)
        
        final_video = overlay.set_audio(audio_clip)
        final_video = final_video.set_duration(final_audio_duration)
        
        # Step 4: Save video (mobile-optimized settings)
        status_text.text("Step 4/4: Saving video...")
        
        output_path = tempfile.NamedTemporaryFile(delete=False, suffix="_mobile.mp4").name
        
        # Get original dimensions
        width, height = overlay.size
        
        # Mobile-optimized encoding settings
        final_video.write_videofile(
            output_path,
            fps=min(30, overlay.fps) if hasattr(overlay, 'fps') else 30,  # Lower FPS for mobile
            codec="libx264",
            audio_codec="aac",
            bitrate="4M",  # Lower bitrate for mobile
            verbose=False,
            logger=None,
            preset='fast',  # Faster encoding for mobile
            threads=2,  # Fewer threads for mobile
            ffmpeg_params=[
                '-movflags', '+faststart',  # Quick start for mobile
                '-profile:v', 'baseline',  # Better mobile compatibility
                '-level', '3.0'
            ]
        )
        
        progress_bar.progress(100)
        status_text.text("Processing complete!")
        time.sleep(0.5)
        
        # Cleanup
        audio_clip.close()
        overlay.close()
        final_video.close()
        
        return output_path, final_audio_duration, width, height
        
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        
        # Mobile-specific error guidance
        if "memory" in str(e).lower():
            st.info("💡 **Mobile Tip:** Try smaller files or restart the app")
        elif "codec" in str(e).lower():
            st.info("💡 **Mobile Tip:** Try converting your video to MP4 format first")
        
        import traceback
        with st.expander("Technical Details"):
            st.code(traceback.format_exc())
        return None, 0, 0, 0
    finally:
        st.session_state.processing = False
        if 'progress_bar' in locals():
            progress_bar.empty()
        if 'status_text' in locals():
            status_text.empty()

# ---------- CREATE BUTTON (MOBILE OPTIMIZED) ----------
st.divider()

# Check if ready to process
files_ready = st.session_state.bg_path and st.session_state.overlay_path
processing_disabled = not files_ready or st.session_state.processing

create_col1, create_col2 = st.columns([3, 1])

with create_col1:
    if st.button("🎬 **CREATE VIDEO**", 
                 type="primary", 
                 disabled=processing_disabled,
                 use_container_width=True):
        
        if not files_ready:
            st.warning("Please upload both files first")
            st.stop()
        
        # Show processing area
        processing_container = st.container()
        
        with processing_container:
            # Process video
            output_path, duration, width, height = process_video_mobile()
            
            if output_path and os.path.exists(output_path):
                st.session_state.last_output_path = output_path
                
                # Success message
                st.success("✅ Video created successfully!")
                
                # Display video with mobile-optimized player
                st.subheader("📺 Your Video")
                
                try:
                    # Read video for display
                    with open(output_path, "rb") as video_file:
                        video_bytes = video_file.read()
                    
                    # Display with mobile-friendly controls
                    st.video(video_bytes, format="video/mp4", start_time=0)
                    
                except Exception as e:
                    st.info("Video preview available for download")
                
                # Video info cards for mobile
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                
                st.subheader("📊 Video Details")
                info_cols = st.columns(3)
                with info_cols[0]:
                    st.metric("Duration", f"{duration:.1f}s")
                with info_cols[1]:
                    st.metric("Resolution", f"{width}×{height}")
                with info_cols[2]:
                    st.metric("Size", f"{file_size:.1f}MB")
                
                # Mobile-friendly download button
                st.subheader("📥 Download")
                with open(output_path, "rb") as f:
                    video_data = f.read()
                
                # Generate filename
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"mobile_video_{width}x{height}_{timestamp}.mp4"
                
                st.download_button(
                    label="⬇️ **DOWNLOAD VIDEO**",
                    data=video_data,
                    file_name=filename,
                    mime="video/mp4",
                    type="primary",
                    use_container_width=True,
                    help="Tap to download to your device"
                )
                
                # Cleanup option for mobile
                with st.expander("🔄 Create Another", expanded=False):
                    if st.button("Clear & Start New", use_container_width=True):
                        cleanup_temp_files()
                        for key in ['bg_path', 'overlay_path', 'bg_clip', 'overlay_clip']:
                            st.session_state[key] = None
                        st.rerun()

with create_col2:
    # Quick status indicator
    if files_ready:
        st.success("Ready")
    elif st.session_state.bg_path or st.session_state.overlay_path:
        st.warning("Need both files")
    else:
        st.info("Upload files")

# ---------- MOBILE-SPECIFIC INSTRUCTIONS ----------
with st.expander("📱 **Mobile Guide**", expanded=False):
    st.markdown("""
    ### 📖 Mobile-Optimized Video Maker
    
    **Perfect for:**
    - Smartphones & Tablets
    - Social media videos
    - Quick edits on the go
    
    **📤 Upload Tips:**
    1. **Background File**: MP3 (audio) or MP4 (video with audio)
    2. **Overlay Video**: MP4 format works best
    3. **File Sizes**: Under 50MB for faster mobile processing
    4. **Internet**: Use WiFi for large files
    
    **✂️ Trimming Guide:**
    - **Audio Trim**: Set start time and duration
    - **Video Trim**: Set start time and duration
    - **Auto-loop**: Video repeats if shorter than audio
    
    **🎬 Processing:**
    - Keep screen ON during processing
    - Don't switch browser tabs
    - Wait for completion message
    
    **📥 Download:**
    - Tap download button
    - Save to Photos/Gallery
    - Share directly to apps
    
    **⚠️ Mobile Limitations:**
    - Large files (>100MB) may fail
    - Processing time varies by device
    - Browser may timeout after 5 minutes
    - iOS Safari has 50MB download limit
    
    **💡 Pro Tips:**
    1. Use landscape videos for better preview
    2. Close other apps before processing
    3. Convert videos to MP4 first
    4. Keep videos under 60 seconds for quick processing
    """)

# ---------- MOBILE TROUBLESHOOTING ----------
with st.expander("🔧 Troubleshooting", expanded=False):
    tab1, tab2, tab3 = st.tabs(["Common Issues", "Browser Tips", "File Help"])
    
    with tab1:
        st.markdown("""
        **❌ Upload fails:**
        - Check file format (MP3/MP4 recommended)
        - Reduce file size (<50MB)
        - Check internet connection
        
        **❌ Processing fails:**
        - Wait 30 seconds, try again
        - Refresh the page
        - Use smaller files
        
        **❌ No audio in result:**
        - Ensure background file has audio
        - Check volume isn't muted
        - Try different audio file
        
        **❌ Can't download:**
        - iOS: Use "Save to Files" option
        - Android: Check Downloads folder
        - Allow downloads in browser settings
        """)
    
    with tab2:
        st.markdown("""
        **📱 Browser Compatibility:**
        - **Chrome Mobile**: Best experience
        - **Safari iOS**: Enable all permissions
        - **Firefox Mobile**: Allow autoplay
        
        **🔧 Browser Settings:**
        1. Enable JavaScript
        2. Allow camera/microphone access
        3. Disable popup blocker
        4. Enable auto-play videos
        
        **🌐 Connection Issues:**
        - Use WiFi for large files
        - Disable VPN if slow
        - Clear browser cache if stuck
        """)
    
    with tab3:
        st.markdown("""
        **📁 Supported Formats:**
        - **Audio**: MP3, M4A, WAV (from video)
        - **Video**: MP4, MOV, AVI
        
        **🔄 Conversion Tools:**
        - Online: CloudConvert, Zamzar
        - Mobile: Video Converter apps
        - Desktop: HandBrake, VLC
        
        **📊 File Size Guide:**
        - 1 min video ≈ 10-20MB
        - HD video ≈ 5MB per 10 seconds
        - Recommended max: 50MB for mobile
        
        **🎞️ Resolution Tips:**
        - 1080p (1920×1080) - Best quality
        - 720p (1280×720) - Good for mobile
        - 480p (854×480) - Fastest processing
        """)

# ---------- FOOTER WITH MOBILE INFO ----------
st.divider()

footer_col1, footer_col2, footer_col3 = st.columns(3)
with footer_col1:
    st.caption(f"Version {APP_VERSION}")
with footer_col2:
    st.caption("Mobile Optimized")
with footer_col3:
    st.caption("No Resizing • Original Quality")

# Auto-cleanup on session end
if not files_ready and st.session_state.last_output_path:
    cleanup_temp_files()
