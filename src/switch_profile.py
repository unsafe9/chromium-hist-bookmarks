#!/usr/bin/python3
# -*- coding: utf-8 -*-
import subprocess
import sys
from Alfred3 import Tools as Tools


def switch_to_profile(app_name: str, profile_dir: str):
    """
    Switch to the specified browser profile using command line.

    Args:
        app_name: Browser application name (e.g., "Google Chrome")
        profile_dir: Profile directory name (e.g., "Default", "Profile 1")
    """
    try:
        # Create command to open browser with specific profile
        if "Chrome" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Brave" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Edge" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Arc" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Vivaldi" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Opera" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Sidekick" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Dia" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        elif "Chromium" in app_name:
            cmd = [
                "open",
                "-na",
                app_name,
                "--args",
                f"--profile-directory={profile_dir}",
            ]
        else:
            # Generic approach for unknown browsers
            cmd = [
                "open",
                "-na",
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
