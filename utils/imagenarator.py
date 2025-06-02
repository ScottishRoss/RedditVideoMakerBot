import os
import re
import textwrap

from PIL import Image, ImageDraw, ImageFont
from rich.progress import track

from TTS.engine_wrapper import process_text
from utils.fonts import getheight, getsize


def draw_multiple_line_text(
    image, text, font, text_color, padding, wrap=50, transparent=False
) -> None:
    """
    Draw multiline text over given image with modern styling
    """
    draw = ImageDraw.Draw(image)
    font_height = getheight(font, text)
    image_width, image_height = image.size
    lines = textwrap.wrap(text, width=wrap)
    
    # Calculate total text block height
    total_height = sum(getheight(font, line) for line in lines) + (len(lines) - 1) * padding
    
    # Calculate starting y position to center the text block
    y = (image_height - total_height) / 2
    
    # Create a semi-transparent background for the text
    if not transparent:
        # Calculate text block dimensions
        max_line_width = max(getsize(font, line)[0] for line in lines)
        text_block_width = max_line_width + 60  # Increased padding
        text_block_height = total_height + 40  # Increased padding
        
        # Calculate background position
        bg_x = (image_width - text_block_width) / 2
        bg_y = y - 20  # Increased padding above text
        
        # Create gradient background with higher opacity
        for i in range(int(text_block_height)):
            alpha = int(200 - (i / text_block_height) * 50)  # Gradient from 200 to 150
            draw.rectangle(
                [(bg_x, bg_y + i), (bg_x + text_block_width, bg_y + i + 1)],
                fill=(0, 0, 0, alpha)
            )
    
    # Draw each line of text
    for line in lines:
        line_width, line_height = getsize(font, line)
        x = (image_width - line_width) / 2
        
        if transparent:
            # Draw text shadow/outline for transparent mode
            shadow_color = (0, 0, 0, 255)  # Solid black for shadow
            # Draw multiple layers of shadow for stronger effect
            for offset_x, offset_y in [(3, 3), (-3, 3), (3, -3), (-3, -3), (0, 3), (0, -3), (3, 0), (-3, 0)]:
                draw.text(
                    (x + offset_x, y + offset_y),
                    line,
                    font=font,
                    fill=shadow_color
                )
        else:
            # Draw text shadow/outline for non-transparent mode
            shadow_color = (0, 0, 0, 200)  # Semi-transparent black
            # Draw multiple layers of shadow for stronger effect
            for offset_x, offset_y in [(3, 3), (-3, 3), (3, -3), (-3, -3), (0, 3), (0, -3), (3, 0), (-3, 0)]:
                draw.text(
                    (x + offset_x, y + offset_y),
                    line,
                    font=font,
                    fill=shadow_color
                )
        
        # Draw main text with increased size and brightness
        draw.text((x, y), line, font=font, fill=text_color)
        y += line_height + padding


def imagemaker(theme, reddit_obj: dict, txtclr, padding=5, transparent=False) -> None:
    """
    Render Images for video
    """
    texts = reddit_obj["thread_post"]
    id = re.sub(r"[^\w\s-]", "", reddit_obj["thread_id"])

    if transparent:
        # Increase font size for better visibility
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 120)
    else:
        # Increase font size for better visibility
        font = ImageFont.truetype(os.path.join("fonts", "Roboto-Bold.ttf"), 120)
    size = (1920, 1080)

    image = Image.new("RGBA", size, theme)

    for idx, text in track(enumerate(texts), "Rendering Image"):
        image = Image.new("RGBA", size, theme)
        text = process_text(text, False)
        draw_multiple_line_text(image, text, font, txtclr, padding, wrap=30, transparent=transparent)
        image.save(f"assets/temp/{id}/png/img{idx}.png")
