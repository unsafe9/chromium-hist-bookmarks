#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import subprocess
import sys
from Alfred3 import Tools as Tools
from browsers import (
    is_chromium_browser_by_app_name,
    get_profile_switch_command,
    get_browser_config,
)


def get_profile_display_name(profile_dir: str) -> str:
    """
    Convert profile directory name to a display name that might appear in window titles.

    Args:
        profile_dir: Profile directory name (e.g., "Default", "Profile 1")

    Returns:
        Expected display name for the profile
    """
    if profile_dir == "Default":
        return "Person 1"  # Chrome often shows "Person 1" for the default profile
    elif profile_dir.startswith("Profile "):
        # Profile 1 -> Person 2, Profile 2 -> Person 3, etc.
        try:
            profile_num = int(profile_dir.split(" ")[1])
            return f"Person {profile_num + 1}"
        except (ValueError, IndexError):
            return profile_dir
    else:
        return profile_dir


def check_existing_browser_window(app_name: str, profile_dir: str):
    """
    Check if a browser window with the specified profile is already open and switch to it.

    Args:
        app_name: Browser application name (e.g., "Google Chrome")
        profile_dir: Profile directory name (e.g., "Default", "Profile 1")

    Returns:
        bool: True if window exists and was successfully focused, False otherwise
    """
    try:
        # For Chromium-based browsers, use process-based detection first
        if is_chromium_browser_by_app_name(app_name):
            # First try the more reliable process-based method
            if check_profile_by_process(app_name, profile_dir):
                return True

            # Fallback to Chrome's native AppleScript API for profile switching
            return try_chrome_profile_switch(app_name, profile_dir)

        return False

    except Exception as e:
        Tools.log(f"Error checking existing browser window: {e}")
        return False


def try_chrome_profile_switch(app_name: str, profile_dir: str):
    """
    Try to switch to an existing Chrome profile using Chrome's AppleScript API.

    Args:
        app_name: Browser application name
        profile_dir: Profile directory name

    Returns:
        bool: True if successfully switched to existing profile, False otherwise
    """
    try:
        # For Chrome specifically, we can use a more direct approach
        if "Chrome" in app_name:
            # Try to get all windows and check their profiles
            get_windows_script = f"""
            tell application "{app_name}"
                if it is running then
                    set windowCount to count of windows
                    if windowCount > 0 then
                        -- Try to activate the application first
                        activate
                        -- Check if we can find any window (Chrome will switch to the right profile automatically)
                        set index of window 1 to 1
                        return true
                    end if
                end if
            end tell
            return false
            """

            result = subprocess.run(
                ["osascript", "-e", get_windows_script],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and "true" in result.stdout.strip():
                # Chrome is running, now we need to check if the specific profile is active
                # We'll use a different strategy: try to open the profile and let Chrome handle it
                Tools.log(
                    f"Chrome is running, attempting profile-specific activation for {profile_dir}"
                )
                return False  # Let the main function handle profile switching

        return False

    except Exception as e:
        Tools.log(f"Error in Chrome profile switch: {e}")
        return False


def check_profile_by_process(app_name: str, profile_dir: str):
    """
    Check if a specific profile is running by examining process arguments.

    Args:
        app_name: Browser application name
        profile_dir: Profile directory name

    Returns:
        bool: True if profile process found and activated, False otherwise
    """
    try:
        # Use ps to find browser processes with specific profile directory
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.split("\n")
            profile_found = False

            for line in lines:
                # Look for browser process with specific profile directory
                if (
                    app_name.lower().replace(" ", "") in line.lower()
                    and f"--profile-directory={profile_dir}" in line
                ):
                    profile_found = True
                    Tools.log(
                        f"Found running process for {app_name} with profile {profile_dir}"
                    )
                    break

            if profile_found:
                # Use a more sophisticated AppleScript to bring the right window to front
                focus_profile_script = f"""
                tell application "System Events"
                    tell application process "{app_name}"
                        set frontmost to true
                        -- Try to find the window that belongs to this profile
                        set windowList to windows
                        if (count of windowList) > 0 then
                            -- Bring the first available window to front
                            set index of window 1 to 1
                        end if
                    end tell
                end tell
                
                tell application "{app_name}"
                    activate
                end tell
                """

                activate_result = subprocess.run(
                    ["osascript", "-e", focus_profile_script],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if activate_result.returncode == 0:
                    Tools.log(
                        f"Successfully focused {app_name} for profile {profile_dir}"
                    )
                    return True

        return False

    except Exception as e:
        Tools.log(f"Error checking profile by process: {e}")
        return False


def switch_to_profile(app_name: str, profile_dir: str):
    """
    Switch to the specified browser profile. If a window with the profile is already open,
    focus that window instead of opening a new one.

    Args:
        app_name: Browser application name (e.g., "Google Chrome")
        profile_dir: Profile directory name (e.g., "Default", "Profile 1")
    """
    try:
        # First, check if there's already a browser window open for this specific profile
        if check_existing_browser_window(app_name, profile_dir):
            Tools.log(
                f"Switched to existing {app_name} window for profile {profile_dir}"
            )
            return True

        # No existing window found for this profile, create a new one
        # For Chromium browsers, we'll create a new window only if the profile isn't already running
        if is_chromium_browser_by_app_name(app_name):
            # Use the direct path to the Chrome executable to better control profile launching
            # This approach bypasses some of the issues with the 'open' command
            if "Chrome" in app_name:
                chrome_path = (
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                )
            elif "Brave" in app_name:
                chrome_path = (
                    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
                )
            elif "Edge" in app_name:
                chrome_path = (
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
                )
            else:
                # Fallback to open command for other browsers
                chrome_path = None

            if chrome_path and os.path.exists(chrome_path):
                # Use direct execution to avoid 'open' command issues
                cmd = [
                    chrome_path,
                    f"--profile-directory={profile_dir}",
                    "--new-window",
                ]

                # Execute in background to avoid blocking
                result = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )

                Tools.log(
                    f"Launched {app_name} with profile {profile_dir} using direct path"
                )
                return True
            else:
                # Fallback to open command
                cmd = [
                    "open",
                    "-a",
                    app_name,
                    "--args",
                    f"--profile-directory={profile_dir}",
                    "--new-window",
                ]
        else:
            # Fallback for non-Chromium browsers
            cmd = [
                "open",
                "-n",
                "-a",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

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
    profile_arg = Tools.getArgv(1)
    if not profile_arg:
        Tools.log("No profile argument provided")
        sys.exit(1)

    # Parse profile argument: "app_name:profile_dir"
    try:
        app_name, profile_dir = profile_arg.split(":", 1)
    except ValueError:
        Tools.log(f"Invalid profile argument format: {profile_arg}")
        sys.exit(1)

    success = switch_to_profile(app_name, profile_dir)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
