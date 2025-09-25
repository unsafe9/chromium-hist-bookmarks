#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import subprocess
import sys
from typing import List, Tuple

from Alfred3 import Items as Items
from Alfred3 import Tools as Tools


def get_chromium_profiles(browser_path: str) -> List[Tuple[str, str, str]]:
    """
    Get all available profiles for a Chromium-based browser.

    Args:
        browser_path (str): Base browser path

    Returns:
        List[Tuple[str, str, str]]: List of tuples in format (profile_dir, real_name, icon_path)
    """
    profiles = []
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if os.path.isfile(local_state_path):
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = json.load(f)

            profile_info_cache = local_state.get("profile", {}).get("info_cache", {})

            for profile_dir, profile_data in profile_info_cache.items():
                real_name = profile_data.get("user_name", profile_dir)

                # Get profile icon path
                icon_path = None
                picture_filename = profile_data.get("gaia_picture_file_name")
                if picture_filename:
                    profile_picture_path = os.path.join(
                        browser_path, profile_dir, picture_filename
                    )
                    if os.path.isfile(profile_picture_path):
                        icon_path = profile_picture_path

                profiles.append((profile_dir, real_name, icon_path))

    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        Tools.log(f"Error reading profiles from {browser_path}: {e}")

    # If no profiles found, add default profile
    if not profiles:
        default_profile_path = os.path.join(browser_path, "Default")
        if os.path.isdir(default_profile_path):
            profiles.append(("Default", "Default Profile", None))

    return profiles


def get_all_browser_profiles() -> List[Tuple[str, str, str, str, str]]:
    """
    Get all available profiles from all supported browsers.

    Returns:
        List[Tuple[str, str, str, str, str]]: List of tuples in format
        (browser_name, app_name, profile_dir, real_name, icon_path)
    """
    all_profiles = []
    user_dir = os.path.expanduser("~")

    # Browser configurations: (env_var, app_name, display_name, browser_path)
    chromium_browsers = [
        (
            "chrome",
            "Google Chrome",
            "Chrome",
            "Library/Application Support/Google/Chrome",
        ),
        (
            "brave",
            "Brave Browser",
            "Brave",
            "Library/Application Support/BraveSoftware/Brave-Browser",
        ),
        (
            "edge",
            "Microsoft Edge",
            "Edge",
            "Library/Application Support/Microsoft Edge",
        ),
        ("arc", "Arc", "Arc", "Library/Application Support/Arc/User Data"),
        ("chromium", "Chromium", "Chromium", "Library/Application Support/Chromium"),
        (
            "opera",
            "Opera",
            "Opera",
            "Library/Application Support/com.operasoftware.Opera",
        ),
        ("vivaldi", "Vivaldi", "Vivaldi", "Library/Application Support/Vivaldi"),
        ("sidekick", "Sidekick", "Sidekick", "Library/Application Support/Sidekick"),
        ("dia", "Dia", "Dia", "Library/Application Support/Dia/User Data"),
    ]

    # Check each browser
    for env_var, app_name, display_name, browser_path in chromium_browsers:
        if Tools.getEnvBool(env_var):
            full_browser_path = os.path.join(user_dir, browser_path)
            if os.path.isdir(full_browser_path):
                profiles = get_chromium_profiles(full_browser_path)
                for profile_dir, real_name, icon_path in profiles:
                    all_profiles.append(
                        (display_name, app_name, profile_dir, real_name, icon_path)
                    )

    return all_profiles


def switch_to_profile(app_name: str, profile_dir: str):
    """
    Switch to the specified browser profile using AppleScript.

    Args:
        app_name: Browser application name (e.g., "Google Chrome")
        profile_dir: Profile directory name (e.g., "Default", "Profile 1")
    """
    try:
        # Create AppleScript to open browser with specific profile
        # Note: Different browsers may have different profile switching methods
        if "Chrome" in app_name:
            # For Chrome, we can use the --profile-directory flag
            applescript = f"""
            do shell script "open -na '{app_name}' --args --profile-directory='{profile_dir}'"
            """
        elif "Brave" in app_name:
            applescript = f"""
            do shell script "open -na '{app_name}' --args --profile-directory='{profile_dir}'"
            """
        elif "Edge" in app_name:
            applescript = f"""
            do shell script "open -na '{app_name}' --args --profile-directory='{profile_dir}'"
            """
        else:
            # For other browsers, try the generic approach
            applescript = f"""
            do shell script "open -na '{app_name}' --args --profile-directory='{profile_dir}'"
            """

        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            Tools.log(f"Successfully switched to profile: {app_name} - {profile_dir}")
            return True
        else:
            Tools.log(
                f"Failed to switch to profile: {app_name} - {profile_dir}, error: {result.stderr}"
            )
            return False

    except Exception as e:
        Tools.log(f"Error switching to profile {app_name} - {profile_dir}: {e}")
        return False


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

    # Get all browser profiles
    all_profiles = get_all_browser_profiles()

    if len(all_profiles) == 0:
        wf.setItem(
            title="No profiles found!",
            subtitle="No browsers installed or enable browsers in workflow settings.",
            valid=False,
        )
        wf.addItem()
        wf.write()
        sys.exit(0)

    # Generate results for all profiles (Alfred will handle filtering)
    for browser_name, app_name, profile_dir, real_name, icon_path in all_profiles:
        display_title = f"{real_name}"
        subtitle = f"[{browser_name}] Switch to {profile_dir} profile"

        # Create argument for profile switching: "app_name:profile_dir"
        arg = f"{app_name}:{profile_dir}"

        wf.setItem(
            title=display_title,
            subtitle=subtitle,
            arg=arg,
        )

        # Set icon
        if icon_path and os.path.isfile(icon_path):
            wf.setIcon(icon_path, "image")
        else:
            wf.setIcon("icon.png")

        wf.addItem()

    wf.write()


if __name__ == "__main__":
    main()
