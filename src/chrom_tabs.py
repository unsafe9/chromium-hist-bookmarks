#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
from typing import List, Tuple

from Alfred3 import Items as Items
from Alfred3 import Tools as Tools
from Favicon import Icons
from browsers import get_enabled_browsers, get_chromium_browsers
from avatar_generator import get_or_create_avatar

# Show favicon in results or default wf icon
show_favicon = Tools.getEnvBool("show_favicon")


def get_real_profile_name(browser_path: str, profile_dir: str) -> str:
    """
    Get real profile name from Local State file

    Args:
        browser_path (str): Base browser path
        profile_dir (str): Profile directory name (Default, Profile 1, etc.)

    Returns:
        str: Real profile name or fallback to directory name
    """
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if os.path.isfile(local_state_path):
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)

            profiles = local_state.get("profile", {}).get("info_cache", {})
            if profile_dir in profiles:
                profile_info = profiles[profile_dir]
                # Try 'name' field first, then 'user_name' - different Chromium browsers use different fields
                real_name = profile_info.get("name") or profile_info.get("user_name") or profile_dir
                return real_name
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        Tools.log(f"Error reading Local State: {e}")

    # Fallback to directory name
    return profile_dir


def get_profile_icon_path(browser_path: str, profile_dir: str, profile_name: str = None) -> str:
    """
    Get profile icon file path from Local State, or generate an avatar

    Args:
        browser_path (str): Base browser path
        profile_dir (str): Profile directory name (Default, Profile 1, etc.)
        profile_name (str): Profile display name (used for avatar generation)

    Returns:
        str: Profile icon file path or None if not found
    """
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if os.path.isfile(local_state_path):
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)

            profiles = local_state.get("profile", {}).get("info_cache", {})
            if profile_dir in profiles:
                profile_info = profiles[profile_dir]
                picture_filename = profile_info.get("gaia_picture_file_name")
                if picture_filename:
                    # Profile pictures are stored in the profile directory
                    profile_picture_path = os.path.join(
                        browser_path, profile_dir, picture_filename
                    )
                    if os.path.isfile(profile_picture_path):
                        return profile_picture_path

                # No profile picture found, generate an avatar
                if profile_name:
                    cache_dir = Tools.getCacheDir()
                    avatar_path = get_or_create_avatar(profile_name, profile_dir, cache_dir)
                    return avatar_path
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        Tools.log(f"Error reading profile icon: {e}")

    return None


def get_chromium_based_tabs(
    app_name: str, browser_name: str
) -> List[Tuple[str, str, str, str]]:
    """
    Get open tabs from Chromium-based browsers.

    Args:
        app_name: The application name for AppleScript (e.g., "Google Chrome", "Brave Browser")
        browser_name: Display name for the browser (e.g., "Chrome", "Brave")

    Returns:
        List[Tuple[str, str, str, str]]: List of tuples in format (title, url, browser_name, tab_id)
    """
    tabs = []
    try:
        # Use AppleScript to get browser tab information with window and tab indices
        applescript = f"""
        tell application "{app_name}"
            if it is running then
                set tabInfo to ""
                set windowIndex to 0
                repeat with w in windows
                    set windowIndex to windowIndex + 1
                    set tabIndex to 0
                    repeat with t in tabs of w
                        set tabIndex to tabIndex + 1
                        set tabInfo to tabInfo & (title of t) & "|||" & (URL of t) & "|||" & windowIndex & "|||" & tabIndex & "\\n"
                    end repeat
                end repeat
                return tabInfo
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            tab_data = result.stdout.strip().split("\n")
            for tab_line in tab_data:
                if "|||" in tab_line:
                    parts = tab_line.split("|||")
                    if len(parts) == 4:
                        title, url, window_idx, tab_idx = parts
                        tab_id = f"{app_name}:{window_idx}:{tab_idx}"
                        tabs.append((title.strip(), url.strip(), browser_name, tab_id))

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
        Tools.log(f"{browser_name} tabs error: {e}")

    return tabs


def get_safari_tabs() -> List[Tuple[str, str, str, str]]:
    """
    Get open tabs from Safari browser.

    Returns:
        List[Tuple[str, str, str, str]]: List of tuples in format (title, url, browser_name, tab_id)
    """
    tabs = []
    try:
        # Use AppleScript to get Safari tab information with window and tab indices
        applescript = """
        tell application "Safari"
            if it is running then
                set tabInfo to ""
                set windowIndex to 0
                repeat with w in windows
                    set windowIndex to windowIndex + 1
                    set tabIndex to 0
                    repeat with t in tabs of w
                        set tabIndex to tabIndex + 1
                        set tabInfo to tabInfo & (name of t) & "|||" & (URL of t) & "|||" & windowIndex & "|||" & tabIndex & "\\n"
                    end repeat
                end repeat
                return tabInfo
            end if
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0 and result.stdout.strip():
            tab_data = result.stdout.strip().split("\n")
            for tab_line in tab_data:
                if "|||" in tab_line:
                    parts = tab_line.split("|||")
                    if len(parts) == 4:
                        title, url, window_idx, tab_idx = parts
                        tab_id = f"Safari:{window_idx}:{tab_idx}"
                        tabs.append((title.strip(), url.strip(), "Safari", tab_id))

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
        Tools.log(f"Safari tabs error: {e}")

    return tabs


def get_all_browser_tabs() -> List[Tuple[str, str, str, str, str, str]]:
    """
    Get open tabs from all supported browsers with profile information.

    Returns:
        List[Tuple[str, str, str, str, str, str]]: List of tuples in format (title, url, browser_name, tab_id, profile_name, profile_icon_path)
    """
    all_tabs = []
    user_dir = os.path.expanduser("~")

    # Check Chromium-based browsers using centralized config
    enabled_browsers = get_enabled_browsers(Tools.getEnvBool)
    for browser_key, config in enabled_browsers:
        if config.is_chromium_based:
            profile_tabs = get_chromium_based_tabs(config.app_name, config.display_name)
            # Add default profile info to each tab for now
            for title, url, browser_name, tab_id in profile_tabs:
                all_tabs.append((title, url, browser_name, tab_id, "Default", None))

    # Check Safari separately (different AppleScript syntax)
    if Tools.getEnvBool("safari"):
        safari_tabs = get_safari_tabs()
        for title, url, browser_name, tab_id in safari_tabs:
            all_tabs.append((title, url, browser_name, tab_id, "Safari", None))

    return all_tabs


def main():
    """Main function"""
    # Log Python version
    Tools.log("PYTHON VERSION:", sys.version)

    # Check Python 3.7 or higher
    if sys.version_info < (3, 7):
        Tools.log("Python version 3.7.0 or higher required!")
        sys.exit(0)

    # Create Alfred workflow item object
    wf = Items()

    # Get all browser tabs
    all_tabs = get_all_browser_tabs()

    if len(all_tabs) == 0:
        wf.setItem(
            title="No open browser tabs found!",
            subtitle="Open browser tabs or enable browsers in workflow settings.",
            valid=False,
        )
        wf.addItem()
        wf.write()
        sys.exit(0)

    # Cache favicons (optional)
    if show_favicon:
        ico_matches = [(url, title) for title, url, _, _, _, _ in all_tabs]
        ico = Icons(ico_matches)

    # Generate results for all tabs (Alfred will handle filtering)
    for title, url, browser_name, tab_id, profile_name, profile_icon_path in all_tabs:
        display_title = title if title else url.split("/")[2] if "/" in url else url
        subtitle = f"{url[:80]}..." if len(url) > 80 else url

        # Include profile name in subtitle if it's not Default
        if profile_name and profile_name != "Default":
            browser_info = f"[{browser_name} - {profile_name}]"
        else:
            browser_info = f"[{browser_name}]"

        wf.setItem(
            title=display_title,
            subtitle=f"{browser_info} {subtitle}",
            arg=tab_id,
            quicklookurl=url,
        )

        if show_favicon:
            favicon = ico.get_favion_path(url)
            if favicon:
                wf.setIcon(favicon, "image")
            else:
                wf.setIcon("icon.png")
        else:
            # Use profile icon when favicon is disabled
            if profile_icon_path and os.path.isfile(profile_icon_path):
                wf.setIcon(profile_icon_path, "image")
            else:
                wf.setIcon("icon.png")

        # Set additional actions
        wf.addMod(key="cmd", subtitle="Other Actions...", arg=url)
        wf.addMod(key="alt", subtitle=url, arg=url)
        wf.addItem()

    wf.write()


if __name__ == "__main__":
    main()
