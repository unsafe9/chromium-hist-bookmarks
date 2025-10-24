#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Avatar generator module for browser profiles.

Generates circular avatar images with the first letter of a profile name
and a color background when no custom profile image is available.

Uses SVG for cross-platform compatibility without external dependencies.
"""

import hashlib
import os
import subprocess


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


def generate_avatar_svg(name: str, output_path: str, size: int = 256) -> str:
    """
    Generate a circular avatar SVG with the first letter of the name.

    Args:
        name (str): Profile name
        output_path (str): Path where to save the generated avatar (will be .png)
        size (int): Size of the avatar image in pixels (default 256)

    Returns:
        str: Path to the generated avatar PNG file
    """
    # Get color for this name
    bg_color = get_color_from_name(name)

    # Get first letter (uppercase)
    letter = name[0].upper() if name else "?"

    # Font size relative to circle size
    font_size = int(size * 0.5)

    # Create SVG content with transparent background
    svg_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">
    <circle cx="{size//2}" cy="{size//2}" r="{size//2}" fill="{bg_color}"/>
    <text x="{size//2}" y="{size//2}"
          font-family="Arial, Helvetica, sans-serif"
          font-size="{font_size}"
          font-weight="bold"
          fill="white"
          text-anchor="middle"
          dominant-baseline="middle">
        {letter}
    </text>
</svg>'''

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Save SVG temporarily
    svg_path = output_path.replace('.png', '.svg')
    with open(svg_path, 'w') as f:
        f.write(svg_content)

    # Return SVG directly - Alfred supports SVG icons with transparency
    svg_output = output_path.replace('.png', '.svg')
    if svg_path != svg_output:
        os.rename(svg_path, svg_output)
    return svg_output


def get_or_create_avatar(profile_name: str, profile_dir: str, cache_dir: str) -> str:
    """
    Get existing avatar or create a new one for a profile.

    Args:
        profile_name (str): Display name of the profile
        profile_dir (str): Profile directory name (used for cache filename)
        cache_dir (str): Directory to cache generated avatars

    Returns:
        str: Path to the avatar image (PNG or SVG), or None if generation fails
    """
    # Create a safe filename from profile_dir
    safe_name = profile_dir.replace(" ", "_").replace("/", "_")
    avatar_path_png = os.path.join(cache_dir, f"avatar_{safe_name}.png")
    avatar_path_svg = os.path.join(cache_dir, f"avatar_{safe_name}.svg")

    # Check if avatar already exists (PNG or SVG)
    if os.path.exists(avatar_path_png):
        return avatar_path_png
    if os.path.exists(avatar_path_svg):
        return avatar_path_svg

    # Generate avatar
    try:
        result = generate_avatar_svg(profile_name, avatar_path_png)
        return result if result and os.path.exists(result) else None
    except Exception as e:
        return None
