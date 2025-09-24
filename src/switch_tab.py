#!/usr/bin/python3
# -*- coding: utf-8 -*-
import subprocess
import sys
from Alfred3 import Tools as Tools


def switch_to_tab(tab_id: str):
    """
    Switch to the specified browser tab using AppleScript.

    Args:
        tab_id: Tab identifier in format "app_name:window_index:tab_index"
    """
    try:
        # Parse tab ID
        parts = tab_id.split(":")
        if len(parts) != 3:
            Tools.log(f"Invalid tab ID format: {tab_id}")
            return False

        app_name, window_idx, tab_idx = parts

        # Create AppleScript to switch to the tab and bring window to front
        applescript = f"""
        tell application "{app_name}"
            activate
            tell window {window_idx}
                set index to 1
            end tell
            delay 0.1
            tell window 1
                set active tab index to {tab_idx}
            end tell
        end tell
        """

        result = subprocess.run(
            ["osascript", "-e", applescript], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            Tools.log(f"Successfully switched to tab: {tab_id}")
            return True
        else:
            Tools.log(f"Failed to switch to tab: {tab_id}, error: {result.stderr}")
            return False

    except Exception as e:
        Tools.log(f"Error switching to tab {tab_id}: {e}")
        return False


def main():
    """Main function"""
    tab_id = Tools.getArgv(1)
    if not tab_id:
        Tools.log("No tab ID provided")
        sys.exit(1)

    success = switch_to_tab(tab_id)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
