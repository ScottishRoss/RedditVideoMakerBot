import json
import random
import re
from pathlib import Path
from random import randrange
from typing import Any, Dict, Tuple

import yt_dlp
from moviepy.editor import AudioFileClip, VideoFileClip
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

from utils import settings
from utils.console import print_step, print_substep

# Load background options at module level
background_options = None

def load_background_options():
    global background_options
    if background_options is not None:
        return background_options
        
    background_options = {}
    # Load background videos
    with open("./utils/background_videos.json") as json_file:
        all_videos = json.load(json_file)
        # Only keep videos that are known to work
        working_videos = {
            "motor-gta": all_videos["motor-gta"],
            "rocket-league": all_videos["rocket-league"],
            "minecraft": all_videos["minecraft"],
            "gta": all_videos["gta"],
            "csgo-surf": all_videos["csgo-surf"],
            "cluster-truck": all_videos["cluster-truck"],
            "minecraft-2": all_videos["minecraft-2"],
            "multiversus": all_videos["multiversus"],
            "fall-guys": all_videos["fall-guys"],
            "steep": all_videos["steep"],
            "satisfying-crafts": all_videos["satisfying-crafts"],
            "satisfying-food": all_videos["satisfying-food"],
        }
        background_options["video"] = working_videos

    # Load background audios
    with open("./utils/background_audios.json") as json_file:
        background_options["audio"] = json.load(json_file)

    # Remove "__comment" from backgrounds
    del background_options["audio"]["__comment"]

    for name in list(background_options["video"].keys()):
        pos = background_options["video"][name][3]

        if pos != "center":
            background_options["video"][name][3] = lambda t: ("center", pos + t)

    return background_options


def get_start_and_end_times(video_length: int, length_of_clip: int) -> Tuple[int, int]:
    """Generates a random interval of time to be used as the background of the video.

    Args:
        video_length (int): Length of the video
        length_of_clip (int): Length of the video to be used as the background

    Returns:
        tuple[int,int]: Start and end time of the randomized interval
    """
    initialValue = 180
    # Issue #1649 - Ensures that will be a valid interval in the video
    while int(length_of_clip) <= int(video_length + initialValue):
        if initialValue == initialValue // 2:
            raise Exception("Your background is too short for this video length")
        else:
            initialValue //= 2  # Divides the initial value by 2 until reach 0
    random_time = randrange(initialValue, int(length_of_clip) - int(video_length))
    return random_time, random_time + video_length


def get_background_config(mode: str):
    """Fetch the background/s configuration"""
    global background_options
    if background_options is None:
        background_options = load_background_options()
        
    # Force random selection if config is empty or not set
    try:
        choice = str(settings.config["settings"]["background"][f"background_{mode}"]).strip()
        if not choice or choice == "":
            choice = random.choice(list(background_options[mode].keys()))
            print_substep(f"Selected random {mode} background: {choice}")
            return background_options[mode][choice]
    except (AttributeError, KeyError):
        pass

    # If we get here, either the config value was invalid or not found
    choice = random.choice(list(background_options[mode].keys()))
    print_substep(f"Selected random {mode} background: {choice}")
    return background_options[mode][choice]


def download_background_video(background_config: Tuple[str, str, str, Any]):
    """Downloads the background/s video from YouTube."""
    Path("./assets/backgrounds/video/").mkdir(parents=True, exist_ok=True)
    # note: make sure the file name doesn't include an - in it
    uri, filename, credit, _ = background_config
    output_path = f"assets/backgrounds/video/{credit}-{filename}"
    
    # Check if file already exists and is valid
    if Path(output_path).is_file():
        try:
            # Verify the file is a valid video file
            with VideoFileClip(output_path) as clip:
                if clip.duration > 0:
                    return
        except Exception:
            # If file is invalid, remove it and download again
            Path(output_path).unlink()
    
    print_step(
        "We need to download the backgrounds videos. they are fairly large but it's only done once. 😎"
    )
    print_substep("Downloading the backgrounds videos... please be patient 🙏 ")
    print_substep(f"Downloading {filename} from {uri}")
    ydl_opts = {
        "format": "best[height<=1080][ext=mp4]/best[height<=1080]/best",
        "outtmpl": output_path,
        "retries": 10,
        "quiet": True,
        "no_warnings": True,
        # Add more robust options to handle restrictions
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "no_color": True,
        "geo_bypass": True,
        "geo_verification_proxy": None,
        # Additional options to bypass restrictions
        "extractor_args": {
            "youtube": {
                "skip": ["dash", "hls"],
                "player_client": ["android", "web"],
                "player_skip": ["js", "configs", "webpage"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try to extract info to verify video is accessible
            info = ydl.extract_info(uri, download=False)
            if not info:
                raise Exception("Could not extract video information")
                
            # Then download the video
            ydl.download(uri)
            
        # Verify the download was successful
        if not Path(output_path).is_file():
            raise Exception("Download completed but file not found")
            
        # Verify the file is a valid video
        with VideoFileClip(output_path) as clip:
            if clip.duration <= 0:
                raise Exception("Downloaded file is not a valid video")
                
        print_substep("Background video downloaded successfully! 🎉", style="bold green")
    except Exception as e:
        error_msg = f"Failed to download background video: {str(e)}"
        print_substep(error_msg, style="bold red")
        print_substep("This video may be private, deleted, or no longer available.", style="bold red")
        print_substep("Please try a different background video in your config.toml file.", style="bold red")
        # Clean up any partial download
        if Path(output_path).is_file():
            Path(output_path).unlink()
        raise Exception(error_msg)


def download_background_audio(background_config: Tuple[str, str, str]):
    """Downloads the background/s audio from YouTube."""
    Path("./assets/backgrounds/audio/").mkdir(parents=True, exist_ok=True)
    # note: make sure the file name doesn't include an - in it
    uri, filename, credit = background_config
    output_path = f"./assets/backgrounds/audio/{credit}-{filename}"
    
    # Check if file already exists and is valid
    if Path(output_path).is_file():
        try:
            # Verify the file is a valid audio file
            with AudioFileClip(output_path) as clip:
                if clip.duration > 0:
                    return
        except Exception:
            # If file is invalid, remove it and download again
            Path(output_path).unlink()
    
    print_step(
        "We need to download the backgrounds audio. they are fairly large but it's only done once. 😎"
    )
    print_substep("Downloading the backgrounds audio... please be patient 🙏 ")
    print_substep(f"Downloading {filename} from {uri}")
    ydl_opts = {
        "outtmpl": output_path,
        "format": "bestaudio/best",
        "extract_audio": True,
        "retries": 10,
        "quiet": True,
        "no_warnings": True,
        # Add more robust options to handle restrictions
        "nocheckcertificate": True,
        "ignoreerrors": True,
        "no_color": True,
        "geo_bypass": True,
        "geo_verification_proxy": None,
        # Additional options to bypass restrictions
        "extractor_args": {
            "youtube": {
                "skip": ["dash", "hls"],
                "player_client": ["android", "web"],
                "player_skip": ["js", "configs", "webpage"]
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache"
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First try to extract info to verify video is accessible
            info = ydl.extract_info(uri, download=False)
            if not info:
                raise Exception("Could not extract video information")
                
            # Then download the audio
            ydl.download([uri])
            
        # Verify the download was successful
        if not Path(output_path).is_file():
            raise Exception("Download completed but file not found")
            
        # Verify the file is a valid audio file
        with AudioFileClip(output_path) as clip:
            if clip.duration <= 0:
                raise Exception("Downloaded file is not a valid audio file")
                
        print_substep("Background audio downloaded successfully! 🎉", style="bold green")
    except Exception as e:
        error_msg = f"Failed to download background audio: {str(e)}"
        print_substep(error_msg, style="bold red")
        print_substep("This audio may be private, deleted, or no longer available.", style="bold red")
        print_substep("Please try a different background audio in your config.toml file.", style="bold red")
        # Clean up any partial download
        if Path(output_path).is_file():
            Path(output_path).unlink()
        raise Exception(error_msg)


def chop_background(background_config: Dict[str, Tuple], video_length: int, reddit_object: dict):
    """Generates the background audio and footage to be used in the video and writes it to assets/temp/background.mp3 and assets/temp/background.mp4

    Args:
        background_config (Dict[str,Tuple]]) : Current background configuration
        video_length (int): Length of the clip where the background footage is to be taken out of
    """
    id = re.sub(r"[^\w\s-]", "", reddit_object["thread_id"])

    if settings.config["settings"]["background"][f"background_audio_volume"] == 0:
        print_step("Volume was set to 0. Skipping background audio creation . . .")
    else:
        print_step("Finding a spot in the backgrounds audio to chop...✂️")
        audio_choice = f"{background_config['audio'][2]}-{background_config['audio'][1]}"
        background_audio = AudioFileClip(f"assets/backgrounds/audio/{audio_choice}")
        start_time_audio, end_time_audio = get_start_and_end_times(
            video_length, background_audio.duration
        )
        background_audio = background_audio.subclip(start_time_audio, end_time_audio)
        background_audio.write_audiofile(f"assets/temp/{id}/background.mp3")

    print_step("Finding a spot in the backgrounds video to chop...✂️")
    video_choice = f"{background_config['video'][2]}-{background_config['video'][1]}"
    background_video = VideoFileClip(f"assets/backgrounds/video/{video_choice}")
    start_time_video, end_time_video = get_start_and_end_times(
        video_length, background_video.duration
    )
    # Extract video subclip
    try:
        ffmpeg_extract_subclip(
            f"assets/backgrounds/video/{video_choice}",
            start_time_video,
            end_time_video,
            targetname=f"assets/temp/{id}/background.mp4",
        )
    except (OSError, IOError):  # ffmpeg issue see #348
        print_substep("FFMPEG issue. Trying again...")
        with VideoFileClip(f"assets/backgrounds/video/{video_choice}") as video:
            new = video.subclip(start_time_video, end_time_video)
            new.write_videofile(f"assets/temp/{id}/background.mp4")
    print_substep("Background video chopped successfully!", style="bold green")
    return background_config["video"][2]


# Create a tuple for downloads background (background_audio_options, background_video_options)
background_options = load_background_options()
