import os
import re
from pytubefix import Playlist, YouTube
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_fixed
import subprocess


# Function to sanitize filenames
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '-', filename)


def download_single_video(video_url, resolution):
    """Download a single video from the given URL."""
    yt = YouTube(video_url, on_progress_callback=progress_function)
    video_streams = yt.streams.filter(res=resolution)

    video_filename = sanitize_filename(f"{yt.title}.mp4")
    video_path = os.path.join(os.getcwd(), video_filename)

    if os.path.exists(video_path):
        print(f"{video_filename} already exists")
        return

    if not video_streams:
        highest_resolution_stream = yt.streams.get_highest_resolution()
        video_name = sanitize_filename(highest_resolution_stream.default_filename)
        print(f"Downloading {video_name} in {highest_resolution_stream.resolution}")
        download_with_retries(highest_resolution_stream, video_path)
    else:
        video_stream = video_streams.first()
        video_name = sanitize_filename(video_stream.default_filename)
        print(f"Downloading video for {video_name} in {resolution}")
        download_with_retries(video_stream, "video.mp4")

        # Download audio
        audio_stream = yt.streams.get_audio_only()
        print(f"Downloading audio for {video_name}")
        download_with_retries(audio_stream, "audio.mp4")

        # Merge video and audio
        print("Merging video and audio...")
        merge_audio_video()

        # Move the final merged file to the appropriate location
        os.rename("final.mp4", video_path)
        os.remove("video.mp4")
        os.remove("audio.mp4")

    print(f"Downloaded and merged: {video_filename}")
    print("----------------------------------")


def download_playlist(playlist_url, resolution):
    """Download all videos from a playlist."""
    playlist = Playlist(playlist_url)
    playlist_name = sanitize_filename(re.sub(r'\W+', '-', playlist.title))

    if not os.path.exists(playlist_name):
        os.mkdir(playlist_name)

    for index, video in enumerate(tqdm(playlist.videos, desc="Downloading playlist", unit="video"), start=1):
        yt = YouTube(video.watch_url, on_progress_callback=progress_function)
        video_streams = yt.streams.filter(res=resolution)

        video_filename = sanitize_filename(f"{index}. {yt.title}.mp4")
        video_path = os.path.join(playlist_name, video_filename)

        if os.path.exists(video_path):
            print(f"{video_filename} already exists")
            continue

        if not video_streams:
            highest_resolution_stream = yt.streams.get_highest_resolution()
            video_name = sanitize_filename(highest_resolution_stream.default_filename)
            print(f"Downloading {video_name} in {highest_resolution_stream.resolution}")
            download_with_retries(highest_resolution_stream, video_path)
        else:
            video_stream = video_streams.first()
            video_name = sanitize_filename(video_stream.default_filename)
            print(f"Downloading video for {video_name} in {resolution}")
            download_with_retries(video_stream, "video.mp4")

            audio_stream = yt.streams.get_audio_only()
            print(f"Downloading audio for {video_name}")
            download_with_retries(audio_stream, "audio.mp4")

            # Merge video and audio
            print("Merging video and audio...")
            merge_audio_video()

            # Move the final merged file to the playlist folder
            os.rename("final.mp4", video_path)
            os.remove("video.mp4")
            os.remove("audio.mp4")

        print("----------------------------------")


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def download_with_retries(stream, filename):
    """Download a stream (video/audio) with retry logic."""
    stream.download(filename=filename)


def merge_audio_video():
    """Merge the downloaded video and audio into one final file using FFmpeg."""
    try:
        command = [
            "ffmpeg", "-y", "-i", "video.mp4", "-i", "audio.mp4", "-c:v", "copy", 
            "-c:a", "aac", "final.mp4", "-loglevel", "quiet", "-stats"
        ]
        subprocess.run(command, check=True)
        print("Merging completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during merging: {e}")
        raise


def progress_function(stream, chunk, bytes_remaining):
    """Display download progress in the terminal."""
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining
    percentage_of_completion = bytes_downloaded / total_size * 100
    print(f"Downloading... {percentage_of_completion:.2f}% complete", end="\r")


def is_playlist(url):
    """Check if the URL is a YouTube playlist or a single video."""
    return "playlist" in url


if __name__ == "__main__":
    playlist_url = input("Enter the URL (video/playlist): ")
    resolutions = ["240p", "360p", "480p", "720p", "1080p", "1440p", "2160p"]
    resolution = input(f"Please select a resolution {resolutions}: ")

    if is_playlist(playlist_url):
        download_playlist(playlist_url, resolution)
    else:
        download_single_video(playlist_url, resolution)
