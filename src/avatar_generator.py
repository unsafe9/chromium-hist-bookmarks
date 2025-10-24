#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Avatar generator module for browser profiles.

Generates circular avatar images with the first letter of a profile name
and a color background when no custom profile image is available.

Uses PIL (Pillow) from system Python for PNG generation with transparency.
"""

import hashlib
import os
import subprocess
import sys


def get_color_from_name(name: str) -> str:
    """
    Generate a consistent color for a given name using hash.

    Args:
        name (str): Profile name

    Returns:
        str: Hex color string
    """
    # Use hash to generate consistent color for the same name
    hash_value = int(hashlib.md5(name.encode()).hexdigest()[:6], 16)

    # Generate pleasant colors (avoid too dark or too bright)
    r = (hash_value >> 16) % 180 + 50  # 50-230
    g = (hash_value >> 8) % 180 + 50   # 50-230
    b = hash_value % 180 + 50           # 50-230

    return f"#{r:02x}{g:02x}{b:02x}"


def generate_avatar_png(name: str, output_path: str, size: int = 256) -> str:
    """
    Generate a circular avatar PNG with the first letter of the name using PIL.

    Args:
        name (str): Profile name
        output_path (str): Path where to save the generated avatar
        size (int): Size of the avatar image in pixels (default 256)

    Returns:
        str: Path to the generated avatar PNG file, or None if failed
    """
    # Get color for this name (hex format)
    bg_color_hex = get_color_from_name(name)

    # Convert hex to RGB tuple
    bg_color = tuple(int(bg_color_hex[i:i+2], 16) for i in (1, 3, 5))

    # Get first letter (uppercase)
    letter = name[0].upper() if name else "?"

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Create a Python script to generate the PNG with PIL
    # This ensures we use a Python that has PIL installed
    script = f'''
import sys
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit(1)

size = {size}
bg_color = {bg_color}
letter = "{letter}"
output_path = "{output_path}"

# Create image with transparent background
img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw circle
draw.ellipse([0, 0, size, size], fill=bg_color)

# Font size
font_size = int(size * 0.5)

# Try to load a font
font = None
try:
    import os
    font_paths = [
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SF-Pro.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
except:
    pass

if font is None:
    font = ImageFont.load_default()

# Calculate text position to center it
try:
    bbox = draw.textbbox((0, 0), letter, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
except:
    text_width = font_size * 0.6
    text_height = font_size

text_x = (size - text_width) / 2
text_y = (size - text_height) / 2

# Draw text in white
draw.text((text_x, text_y), letter, fill=(255, 255, 255, 255), font=font)

# Save image as PNG
img.save(output_path, 'PNG')
print(output_path)
'''

    # Try to run with system Python that has PIL
    python_paths = [
        '/usr/local/bin/python3',
        '/opt/homebrew/bin/python3',
        '/usr/bin/python3',
        sys.executable
    ]

    for python_path in python_paths:
        if not os.path.exists(python_path):
            continue

        try:
            result = subprocess.run(
                [python_path, '-c', script],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path
        except (subprocess.TimeoutExpired, Exception):
            continue

    return None


def get_or_create_avatar(profile_name: str, profile_dir: str, cache_dir: str) -> str:
    """
    Get existing avatar or create a new one for a profile.

    Args:
        profile_name (str): Display name of the profile
        profile_dir (str): Profile directory name (used for cache filename)
        cache_dir (str): Directory to cache generated avatars

    Returns:
        str: Path to the avatar image PNG, or None if generation fails
    """
    # Create a safe filename from profile_dir
    safe_name = profile_dir.replace(" ", "_").replace("/", "_")
    avatar_path_png = os.path.join(cache_dir, f"avatar_{safe_name}.png")

    # Check if avatar already exists
    if os.path.exists(avatar_path_png):
        return avatar_path_png

    # Generate avatar using PIL via subprocess
    try:
        result = generate_avatar_png(profile_name, avatar_path_png)
        return result if result and os.path.exists(result) else None
    except Exception as e:
        return None
