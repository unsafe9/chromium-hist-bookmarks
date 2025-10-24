#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Avatar generator module for browser profiles.

Generates circular avatar images with the first letter of a profile name
and a color background when no custom profile image is available.
"""

import hashlib
import os
from PIL import Image, ImageDraw, ImageFont


def get_color_from_name(name: str) -> tuple:
    """
    Generate a consistent color for a given name using hash.

    Args:
        name (str): Profile name

    Returns:
        tuple: RGB color tuple
    """
    # Use hash to generate consistent color for the same name
    hash_value = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)

    # Generate pleasant colors (avoid too dark or too bright)
    r = (hash_value >> 16) % 180 + 50  # 50-230
    g = (hash_value >> 8) % 180 + 50   # 50-230
    b = hash_value % 180 + 50           # 50-230

    return (r, g, b)


def generate_avatar(name: str, output_path: str, size: int = 256) -> str:
    """
    Generate a circular avatar image with the first letter of the name.

    Args:
        name (str): Profile name
        output_path (str): Path where to save the generated avatar
        size (int): Size of the avatar image in pixels (default 256)

    Returns:
        str: Path to the generated avatar image
    """
    # Create image with transparent background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Get color for this name
    bg_color = get_color_from_name(name)

    # Draw circle
    draw.ellipse([0, 0, size, size], fill=bg_color)

    # Get first letter (uppercase)
    letter = name[0].upper() if name else "?"

    # Try to use a system font
    font_size = int(size * 0.5)
    try:
        # Try different font paths for macOS
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSDisplay.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        font = None
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue

        if font is None:
            # Fallback to default font
            font = ImageFont.load_default()
    except:
        # Use default font if all else fails
        font = ImageFont.load_default()

    # Calculate text position to center it
    # For default font, estimate position
    if hasattr(font, 'getbbox'):
        bbox = font.getbbox(letter)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        # Fallback for older PIL versions or default font
        text_width = font_size * 0.6
        text_height = font_size

    text_x = (size - text_width) / 2
    text_y = (size - text_height) / 2

    # Draw text in white
    draw.text((text_x, text_y), letter, fill=(255, 255, 255, 255), font=font)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Save image
    img.save(output_path, 'PNG')

    return output_path


def get_or_create_avatar(profile_name: str, profile_dir: str, cache_dir: str) -> str:
    """
    Get existing avatar or create a new one for a profile.

    Args:
        profile_name (str): Display name of the profile
        profile_dir (str): Profile directory name (used for cache filename)
        cache_dir (str): Directory to cache generated avatars

    Returns:
        str: Path to the avatar image
    """
    # Create a safe filename from profile_dir
    safe_name = profile_dir.replace(" ", "_").replace("/", "_")
    avatar_path = os.path.join(cache_dir, f"avatar_{safe_name}.png")

    # Generate avatar if it doesn't exist
    if not os.path.exists(avatar_path):
        generate_avatar(profile_name, avatar_path)

    return avatar_path
