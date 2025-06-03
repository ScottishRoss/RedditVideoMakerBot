import multiprocessing
import os
import re
import tempfile
import textwrap
import threading
import time
from datetime import datetime
from os.path import exists  # Needs to be imported specifically
from pathlib import Path
from typing import Dict, Final, Tuple

import ffmpeg
import translators
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.progress import track

from utils import settings
from utils.cleanup import cleanup
from utils.console import print_step, print_substep
from utils.fonts import getheight
from utils.thumbnail import create_thumbnail
from utils.videos import save_data

console = Console()


class ProgressFfmpeg(threading.Thread):
    def __init__(self, vid_duration_seconds, progress_update_callback):
        threading.Thread.__init__(self, name="ProgressFfmpeg")
        self.stop_event = threading.Event()
        self.output_file = tempfile.NamedTemporaryFile(mode="w+", delete=False)
        self.vid_duration_seconds = vid_duration_seconds
        self.progress_update_callback = progress_update_callback

    def run(self):
        while not self.stop_event.is_set():
            latest_progress = self.get_latest_ms_progress()
            if latest_progress is not None:
                completed_percent = latest_progress / self.vid_duration_seconds
                self.progress_update_callback(completed_percent)
            time.sleep(1)

    def get_latest_ms_progress(self):
        lines = self.output_file.readlines()

        if lines:
            for line in lines:
                if "out_time_ms" in line:
                    out_time_ms_str = line.split("=")[1].strip()
                    if out_time_ms_str.isnumeric():
                        return float(out_time_ms_str) / 1000000.0
                    else:
                        # Handle the case when "N/A" is encountered
                        return None
        return None

    def stop(self):
        self.stop_event.set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()


def name_normalize(name: str) -> str:
    name = re.sub(r'[?\\"%*:|<>]', "", name)
    name = re.sub(r"( [w,W]\s?\/\s?[o,O,0])", r" without", name)
    name = re.sub(r"( [w,W]\s?\/)", r" with", name)
    name = re.sub(r"(\d+)\s?\/\s?(\d+)", r"\1 of \2", name)
    name = re.sub(r"(\w+)\s?\/\s?(\w+)", r"\1 or \2", name)
    name = re.sub(r"\/", r"", name)

    lang = settings.config["reddit"]["thread"]["post_lang"]
    if lang:
        print_substep("Translating filename...")
        translated_name = translators.translate_text(name, translator="google", to_language=lang)
        return translated_name
    else:
        return name


def prepare_background(reddit_id: str, W: int, H: int) -> str:
    output_path = f"assets/temp/{reddit_id}/background_noaudio.mp4"
    output = (
        ffmpeg.input(f"assets/temp/{reddit_id}/background.mp4")
        .filter("crop", f"ih*({W}/{H})", "ih")
        .output(
            output_path,
            an=None,
            **{
                "c:v": "h264",
                "b:v": "20M",
                "b:a": "192k",
                "threads": multiprocessing.cpu_count(),
            },
        )
        .overwrite_output()
    )
    try:
        output.run(quiet=True)
    except ffmpeg.Error as e:
        print(e.stderr.decode("utf8"))
        exit(1)
    return output_path


def create_fancy_thumbnail(image, text, text_color, padding, wrap=35):
    print_step(f"Creating fancy thumbnail for: {text}")
    font_title_size = 47
    font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), font_title_size)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=wrap)
    y = (
        (image_height / 2)
        - (((getheight(font, text) + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
        + 30
    )
    draw = ImageDraw.Draw(image)

    username_font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 30)
    draw.text(
        (205, 825),
        settings.config["settings"]["channel_name"],
        font=username_font,
        fill=text_color,
        align="left",
    )

    if len(lines) == 3:
        lines = textwrap.wrap(text, width=wrap + 10)
        font_title_size = 40
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), font_title_size)
        y = (
            (image_height / 2)
            - (((getheight(font, text) + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
            + 35
        )
    elif len(lines) == 4:
        lines = textwrap.wrap(text, width=wrap + 10)
        font_title_size = 35
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), font_title_size)
        y = (
            (image_height / 2)
            - (((getheight(font, text) + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
            + 40
        )
    elif len(lines) > 4:
        lines = textwrap.wrap(text, width=wrap + 10)
        font_title_size = 30
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), font_title_size)
        y = (
            (image_height / 2)
            - (((getheight(font, text) + (len(lines) * padding) / len(lines)) * len(lines)) / 2)
            + 30
        )

    for line in lines:
        draw.text((120, y), line, font=font, fill=text_color, align="left")
        y += getheight(font, line) + padding

    return image


def merge_background_audio(audio: ffmpeg, reddit_id: str):
    """Gather an audio and merge with assets/backgrounds/background.mp3
    Args:
        audio (ffmpeg): The TTS final audio but without background.
        reddit_id (str): The ID of subreddit
    """
    background_audio_volume = settings.config["settings"]["background"]["background_audio_volume"]
    if background_audio_volume == 0:
        return audio  # Return the original audio
    else:
        # sets volume to config
        bg_audio = ffmpeg.input(f"assets/temp/{reddit_id}/background.mp3").filter(
            "volume",
            background_audio_volume,
        )
        # Merges audio and background_audio
        merged_audio = ffmpeg.filter([audio, bg_audio], "amix", duration="longest")
        return merged_audio  # Return merged audio


def make_final_video(
    number_of_clips: int,
    length: int,
    reddit_obj: dict,
    background_config: Dict[str, Tuple],
) -> str:
    """Gathers audio clips, gathers all screenshots, stitches them together and saves the final video to assets/temp
    Args:
        number_of_clips (int): Index to end at when going through the screenshots'
        length (int): Length of the video
        reddit_obj (dict): The reddit object that contains the posts to read.
        background_config (Tuple[str, str, str, Any]): The background config to use.
    Returns:
        str: Path to the created video file
    """
    # settings values
    W: Final[int] = int(settings.config["settings"]["resolution_w"])
    H: Final[int] = int(settings.config["settings"]["resolution_h"])
    opacity = settings.config["settings"]["opacity"]
    settingsbackground = settings.config["settings"]["background"]

    reddit_id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    allowOnlyTTSFolder: bool = (
        settings.config["settings"]["background"]["enable_extra_audio"]
        and settings.config["settings"]["background"]["background_audio_volume"] != 0
    )

    print_step("Creating the final video 🎥")

    # Create date-based folder structure
    current_date = datetime.now().strftime("%Y-%m-%d")
    base_path = f"./results/{current_date}"
    
    if not exists(base_path):
        print_substep(f"Creating date-based folder: {current_date}")
        os.makedirs(base_path)

    # Create subreddit folder inside date folder
    subreddit = settings.config["reddit"]["thread"]["subreddit"]
    if '+' in subreddit:
        subreddit_dir = "multi_subreddit"
    else:
        subreddit_dir = subreddit

    subreddit_path = f"{base_path}/{subreddit_dir}"
    if not exists(subreddit_path):
        print_substep(f"Creating subreddit folder: {subreddit_dir}")
        os.makedirs(subreddit_path)

    if allowOnlyTTSFolder:
        only_tts_path = f"{subreddit_path}/OnlyTTS"
        if not exists(only_tts_path):
            print_substep("Creating OnlyTTS folder")
            os.makedirs(only_tts_path)

    # Update paths to use date-based structure
    if settingsbackground["background_thumbnail"]:
        thumbnails_path = f"{subreddit_path}/thumbnails"
        if not exists(thumbnails_path):
            print_substep("Creating thumbnails folder")
            os.makedirs(thumbnails_path)

    background_clip = ffmpeg.input(prepare_background(reddit_id, W=W, H=H))

    # Gather all audio clips
    audio_clips = list()
    if number_of_clips == 0 and settings.config["settings"]["storymode"] == "false":
        print(
            "No audio clips to gather. Please use a different TTS or post."
        )
        exit()
    
    # Function to verify audio file exists and has content
    def verify_audio_file(file_path: str) -> bool:
        if not os.path.exists(file_path):
            print(f"Error: Audio file not found: {file_path}")
            return False
        try:
            probe = ffmpeg.probe(file_path)
            if float(probe["format"]["duration"]) <= 0:
                print(f"Error: Audio file has no content: {file_path}")
                return False
            return True
        except Exception as e:
            print(f"Error verifying audio file {file_path}: {str(e)}")
            return False

    # Add title audio
    title_audio = f"assets/temp/{reddit_id}/mp3/title.mp3"
    if not verify_audio_file(title_audio):
        raise Exception("Missing or invalid title audio file")
    
    # Use title audio without speed modifications
    title_clip = ffmpeg.input(title_audio)
    audio_clips.append(title_clip)
    
    # Get the duration of the title audio file
    probe = ffmpeg.probe(title_audio)
    original_duration = float(probe["format"]["duration"])
    audio_clips_durations = [original_duration]

    # Add all other audio clips without speed adjustment
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"] == 0:
            # Single post method
            audio_file = f"assets/temp/{reddit_id}/mp3/post.mp3"
            if not verify_audio_file(audio_file):
                raise Exception(f"Missing or invalid audio file: {audio_file}")
            
            audio_clip = ffmpeg.input(audio_file)
            audio_clips.append(audio_clip)
            
            # Get the duration of the original audio file
            probe = ffmpeg.probe(audio_file)
            original_duration = float(probe["format"]["duration"])
            audio_clips_durations.append(original_duration)
        elif settings.config["settings"]["storymodemethod"] == 1:
            # Multiple post method
            for i in range(number_of_clips):
                audio_file = f"assets/temp/{reddit_id}/mp3/post-{i}.mp3"
                if not verify_audio_file(audio_file):
                    raise Exception(f"Missing or invalid audio file: {audio_file}")
                
                audio_clip = ffmpeg.input(audio_file)
                audio_clips.append(audio_clip)
                
                # Get the duration of the original audio file
                probe = ffmpeg.probe(audio_file)
                original_duration = float(probe["format"]["duration"])
                audio_clips_durations.append(original_duration)
    else:
        # Comment mode
        for i in range(0, number_of_clips):
            audio_file = f"assets/temp/{reddit_id}/mp3/{i}.mp3"
            if not verify_audio_file(audio_file):
                raise Exception(f"Missing or invalid audio file: {audio_file}")
            
            audio_clip = ffmpeg.input(audio_file)
            audio_clips.append(audio_clip)
            
            # Get the duration of the original audio file
            probe = ffmpeg.probe(audio_file)
            original_duration = float(probe["format"]["duration"])
            audio_clips_durations.append(original_duration)

    # Add ending audio without speed adjustment
    ending_audio = f"assets/temp/{reddit_id}/mp3/ending.mp3"
    if not verify_audio_file(ending_audio):
        raise Exception("Missing or invalid ending audio file")
    
    ending_clip = ffmpeg.input(ending_audio)
    audio_clips.append(ending_clip)

    # Concatenate audio with error handling
    try:
        audio_concat = ffmpeg.concat(*audio_clips, a=1, v=0)
        ffmpeg.output(
            audio_concat, f"assets/temp/{reddit_id}/audio.mp3", **{"b:a": "192k"}
        ).overwrite_output().run(quiet=True)
    except ffmpeg.Error as e:
        print(f"Error concatenating audio: {e.stderr.decode('utf8')}")
        raise Exception("Failed to concatenate audio files")

    console.log(f"[bold green] Video Will Be: {length} Seconds Long")

    screenshot_width = int((W * 45) // 100)
    audio = ffmpeg.input(f"assets/temp/{reddit_id}/audio.mp3")
    final_audio = merge_background_audio(audio, reddit_id)

    image_clips = list()

    Path(f"assets/temp/{reddit_id}/png").mkdir(parents=True, exist_ok=True)

    # Credits to tim (beingbored)
    # get the title_template image and draw a text in the middle part of it with the title of the thread
    title_template = Image.open("assets/title_template.png")

    title = reddit_obj["thread_title"]

    title = name_normalize(title)

    font_color = "#000000"
    padding = 5

    # create_fancy_thumbnail(image, text, text_color, padding
    title_img = create_fancy_thumbnail(title_template, title, font_color, padding)

    title_img.save(f"assets/temp/{reddit_id}/png/title.png")
    image_clips.insert(
        0,
        ffmpeg.input(f"assets/temp/{reddit_id}/png/title.png")["v"].filter(
            "scale", screenshot_width, -1
        ),
    )

    current_time = 0
    if settings.config["settings"]["storymode"]:
        if settings.config["settings"]["storymodemethod"] == 0:
            # Show title during silence
            background_clip = background_clip.overlay(
                image_clips[0],
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[0]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[0]

            # Show content with TTS
            image_clips.insert(
                1,
                ffmpeg.input(f"assets/temp/{reddit_id}/png/story_content.png").filter(
                    "scale", screenshot_width, -1
                ),
            )
            background_clip = background_clip.overlay(
                image_clips[1],
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[1]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[1]
        elif settings.config["settings"]["storymodemethod"] == 1:
            # Show title during silence
            background_clip = background_clip.overlay(
                image_clips[0],
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[0]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[0]

            # Show content slides with TTS
            for i in track(range(0, number_of_clips), "Collecting the image files..."):
                image_clips.append(
                    ffmpeg.input(f"assets/temp/{reddit_id}/png/img{i}.png")["v"].filter(
                        "scale", screenshot_width, -1
                    )
                )
                background_clip = background_clip.overlay(
                    image_clips[i + 1],
                    enable=f"between(t,{current_time},{current_time + audio_clips_durations[i + 1]})",
                    x="(main_w-overlay_w)/2",
                    y="(main_h-overlay_h)/2",
                )
                current_time += audio_clips_durations[i + 1]
    else:
        # Show title during silence
        background_clip = background_clip.overlay(
            image_clips[0],
            enable=f"between(t,{current_time},{current_time + audio_clips_durations[0]})",
            x="(main_w-overlay_w)/2",
            y="(main_h-overlay_h)/2",
        )
        current_time += audio_clips_durations[0]

        # Show comments with TTS
        for i in range(0, number_of_clips):
            image_clips.append(
                ffmpeg.input(f"assets/temp/{reddit_id}/png/comment_{i}.png")["v"].filter(
                    "scale", screenshot_width, -1
                )
            )
            image_overlay = image_clips[i + 1].filter("colorchannelmixer", aa=opacity)
            background_clip = background_clip.overlay(
                image_overlay,
                enable=f"between(t,{current_time},{current_time + audio_clips_durations[i + 1]})",
                x="(main_w-overlay_w)/2",
                y="(main_h-overlay_h)/2",
            )
            current_time += audio_clips_durations[i + 1]

    title = re.sub(r"[^\w\s-]", "", reddit_obj["thread_title"])
    idx = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])
    title_thumb = reddit_obj["thread_title"]

    filename = f"{name_normalize(title)[:251]}"

    # create a thumbnail for the video
    if settingsbackground["background_thumbnail"]:
        if not exists(f"{subreddit_path}/thumbnails"):
            print_substep(
                "The 'results/thumbnails' folder could not be found so it was automatically created."
            )
            os.makedirs(f"{subreddit_path}/thumbnails")
        # get the first file with the .png extension from assets/backgrounds and use it as a background for the thumbnail
        first_image = next(
            (file for file in os.listdir("assets/backgrounds") if file.endswith(".png")),
            None,
        )
        if first_image is None:
            print_substep("No png files found in assets/backgrounds", "red")

        else:
            font_family = settingsbackground["background_thumbnail_font_family"]
            font_size = settingsbackground["background_thumbnail_font_size"]
            font_color = settingsbackground["background_thumbnail_font_color"]
            thumbnail = Image.open(f"assets/backgrounds/{first_image}")
            width, height = thumbnail.size
            thumbnailSave = create_thumbnail(
                thumbnail,
                font_family,
                font_size,
                font_color,
                width,
                height,
                title_thumb,
            )
            thumbnailSave.save(f"./assets/temp/{reddit_id}/thumbnail.png")
            print_substep(f"Thumbnail - Building Thumbnail in assets/temp/{reddit_id}/thumbnail.png")

    text = f"Background by {background_config['video'][2]}"
    background_clip = ffmpeg.drawtext(
        background_clip,
        text=text,
        x=f"(w-text_w)",
        y=f"(h-text_h)",
        fontsize=5,
        fontcolor="White",
        fontfile=os.path.join("fonts", "Roboto-Regular.ttf"),
    )

    # Add progress bar
    # First draw the background bar
    background_clip = ffmpeg.drawbox(
        background_clip,
        x="0",
        y="(h-10)",  # 10 pixels from bottom
        width="iw",  # Use input width
        height="5",  # 5 pixels height
        color="black@0.5",  # Semi-transparent black
        t="fill"
    )
    
    # Then draw the progress bar that fills up
    background_clip = ffmpeg.drawbox(
        background_clip,
        x="0",
        y="(h-10)",  # 10 pixels from bottom
        width="(iw*t/67)",  # Dynamic width based on current time (67 seconds total)
        height="5",  # 5 pixels height
        color="white@0.8",  # Semi-transparent white
        t="fill"
    )

    background_clip = background_clip.filter("scale", W, H)
    print_step("Rendering the video 🎥")
    from tqdm import tqdm

    pbar = tqdm(total=100, desc="Progress: ", bar_format="{l_bar}{bar}", unit=" %")

    def on_update_example(progress) -> None:
        status = round(progress * 100, 2)
        old_percentage = pbar.n
        pbar.update(status - old_percentage)

    defaultPath = subreddit_path
    with ProgressFfmpeg(length, on_update_example) as progress:
        path = defaultPath + f"/{filename}"
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this.
        try:
            ffmpeg.output(
                background_clip,
                final_audio,
                path,
                f="mp4",
                **{
                    "c:v": "h264",
                    "b:v": "20M",
                    "b:a": "192k",
                    "threads": multiprocessing.cpu_count(),
                },
            ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                quiet=True,
                overwrite_output=True,
                capture_stdout=False,
                capture_stderr=False,
            )
        except ffmpeg.Error as e:
            print(e.stderr.decode("utf8"))
            exit(1)
    old_percentage = pbar.n
    pbar.update(100 - old_percentage)
    if allowOnlyTTSFolder:
        path = f"{subreddit_path}/OnlyTTS/{filename}"
        path = (
            path[:251] + ".mp4"
        )  # Prevent a error by limiting the path length, do not change this.
        print_step("Rendering the Only TTS Video 🎥")
        with ProgressFfmpeg(length, on_update_example) as progress:
            try:
                ffmpeg.output(
                    background_clip,
                    audio,
                    path,
                    f="mp4",
                    **{
                        "c:v": "h264",
                        "b:v": "20M",
                        "b:a": "192k",
                        "threads": multiprocessing.cpu_count(),
                    },
                ).overwrite_output().global_args("-progress", progress.output_file.name).run(
                    quiet=True,
                    overwrite_output=True,
                    capture_stdout=False,
                    capture_stderr=False,
                )
            except ffmpeg.Error as e:
                print(e.stderr.decode("utf8"))
                exit(1)

        old_percentage = pbar.n
        pbar.update(100 - old_percentage)
    pbar.close()
    save_data(subreddit, filename + ".mp4", title, idx, background_config["video"][2])
    print_step("Removing temporary files 🗑")
    cleanups = cleanup(reddit_id)
    print_substep(f"Removed {cleanups} temporary files 🗑")
    print_step("Done! 🎉 The video is in the results folder 📁")
    
    return path  # Return the path to the created video file
