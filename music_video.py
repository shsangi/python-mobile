# Replace st.video() with this:
def display_video_with_fallback(video_path):
    """Display video with fallback for mobile compatibility"""
    try:
        # Try direct display first
        st.video(video_path)
    except:
        # Fallback: create download link with preview
        st.warning("Preview might not display in all browsers. Download to view.")
        
        # Show video info
        from moviepy.editor import VideoFileClip
        clip = VideoFileClip(video_path, audio=False)
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Resolution", f"{clip.w}×{clip.h}")
        with col2:
            st.metric("Duration", f"{clip.duration:.1f}s")
        clip.close()
