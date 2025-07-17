import subprocess

def video_to_webp(src_path, dest_path, duration=10):
    cmd = [
        "ffmpeg",
        "-i", src_path,
        "-t", str(duration),
        "-vf", "fps=10,scale=800:-1",
        "-loop", "0",
        "-preset", "picture",
        "-an",
        "-f", "webp",           # <---- Explicitly set output format
        dest_path
    ]
    subprocess.run(cmd, check=True)

def video_to_webm(src_path, dest_path, duration=None):
    """
    Converts a video to WebM using VP9 (high quality, small size).
    Optionally, trim to 'duration' seconds.
    """
    cmd = [
        "ffmpeg",
        "-i", src_path,
        "-c:v", "libvpx-vp9",    # VP9 codec
        "-b:v", "1M",            # 1 Mbps bitrate (adjust as needed)
        "-c:a", "libopus",       # Opus audio (best for WebM)
    ]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [dest_path]
    subprocess.run(cmd, check=True)


def video_to_mp4(src_path, dest_path, duration=None):
    """
    Converts a video to a standardized MP4 using ffmpeg.
    Optionally, trim to 'duration' seconds.
    Keeps audio.
    """
    cmd = [
        "ffmpeg",
        "-i", src_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "24",         # Adjust for quality/size tradeoff (lower=better)
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart"
    ]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [dest_path]
    subprocess.run(cmd, check=True)

def video_to_mp4_cuda(src_path, dest_path, duration=None):
    cmd = [
        "ffmpeg",
        "-hwaccel", "cuda",
        "-i", src_path,
        "-c:v", "h264_nvenc",
        "-preset", "fast",
        "-b:v", "2M",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart"
    ]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [dest_path]
    subprocess.run(cmd, check=True)

#video_to_webp("videos/1.mp4", "output/video_1.webp", 175)
#video_to_mp4("videos/1.mp4", "output/video_1.mp4", 175)
#video_to_mp4_cuda("videos/1.mp4", "output/video_1.mp4", 175)
video_to_webm("videos/1.mp4", "output/video_1.mp4", 175)
