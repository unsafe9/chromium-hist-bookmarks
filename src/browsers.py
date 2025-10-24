#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Browser configuration module for Chromium History and Bookmarks Alfred Workflow.

This module centralizes all browser-related configurations including:
- Browser names and identifiers
- File system paths
- AppleScript application names
- Browser-specific settings

All browser configurations are organized to minimize duplication between
Chromium-based browsers while supporting browser-specific customizations.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import os


@dataclass
class BrowserConfig:
    """Configuration for a single browser."""

    # Identifiers
    env_key: str  # Environment variable key (e.g., "chrome")
    display_name: str  # Display name (e.g., "Chrome")
    app_name: str  # AppleScript application name (e.g., "Google Chrome")

    # File paths (relative to user home directory)
    data_path: str  # Path to browser data directory

    # Browser characteristics
    is_chromium_based: bool = True  # Whether this is a Chromium-based browser
    supports_profiles: bool = True  # Whether browser supports multiple profiles

    # Optional customizations
    bookmark_file: str = "Bookmarks"  # Name of bookmark file
    history_file: str = "History"  # Name of history file
    local_state_file: str = "Local State"  # Name of local state file


# Chromium-based browsers configuration
CHROMIUM_BROWSERS = {
    "chrome": BrowserConfig(
        env_key="chrome",
        display_name="Chrome",
        app_name="Google Chrome",
        data_path="Library/Application Support/Google/Chrome",
    ),
    "brave": BrowserConfig(
        env_key="brave",
        display_name="Brave",
        app_name="Brave Browser",
        data_path="Library/Application Support/BraveSoftware/Brave-Browser",
    ),
    "brave_beta": BrowserConfig(
        env_key="brave_beta",
        display_name="Brave Beta",
        app_name="Brave Browser Beta",
        data_path="Library/Application Support/BraveSoftware/Brave-Browser-Beta",
    ),
    "edge": BrowserConfig(
        env_key="edge",
        display_name="Edge",
        app_name="Microsoft Edge",
        data_path="Library/Application Support/Microsoft Edge",
    ),
    "chromium": BrowserConfig(
        env_key="chromium",
        display_name="Chromium",
        app_name="Chromium",
        data_path="Library/Application Support/Chromium",
    ),
    "opera": BrowserConfig(
        env_key="opera",
        display_name="Opera",
        app_name="Opera",
        data_path="Library/Application Support/com.operasoftware.Opera",
    ),
    "vivaldi": BrowserConfig(
        env_key="vivaldi",
        display_name="Vivaldi",
        app_name="Vivaldi",
        data_path="Library/Application Support/Vivaldi",
    ),
    "arc": BrowserConfig(
        env_key="arc",
        display_name="Arc",
        app_name="Arc",
        data_path="Library/Application Support/Arc/User Data",
    ),
    "sidekick": BrowserConfig(
        env_key="sidekick",
        display_name="Sidekick",
        app_name="Sidekick",
        data_path="Library/Application Support/Sidekick",
    ),
    "dia": BrowserConfig(
        env_key="dia",
        display_name="Dia",
        app_name="Dia",
        data_path="Library/Application Support/Dia/User Data",
    ),
}

# Non-Chromium browsers
OTHER_BROWSERS = {
    "safari": BrowserConfig(
        env_key="safari",
        display_name="Safari",
        app_name="Safari",
        data_path="Library/Safari",
        is_chromium_based=False,
        supports_profiles=False,
        bookmark_file="Bookmarks.plist",
        history_file="History.db",
        local_state_file=None,
    ),
}

# Combined browser configurations
ALL_BROWSERS = {**CHROMIUM_BROWSERS, **OTHER_BROWSERS}


def get_browser_config(browser_key: str) -> Optional[BrowserConfig]:
    """
    Get browser configuration by key.

    Args:
        browser_key: Browser identifier (e.g., "chrome", "safari")

    Returns:
        BrowserConfig object or None if not found
    """
    return ALL_BROWSERS.get(browser_key)


def get_chromium_browsers() -> Dict[str, BrowserConfig]:
    """Get all Chromium-based browser configurations."""
    return CHROMIUM_BROWSERS


def get_all_browsers() -> Dict[str, BrowserConfig]:
    """Get all browser configurations."""
    return ALL_BROWSERS


def is_chromium_browser(browser_key: str) -> bool:
    """
    Check if a browser is Chromium-based.

    Args:
        browser_key: Browser identifier

    Returns:
        True if browser is Chromium-based, False otherwise
    """
    config = get_browser_config(browser_key)
    return config.is_chromium_based if config else False


def is_chromium_browser_by_app_name(app_name: str) -> bool:
    """
    Check if a browser is Chromium-based by its application name.

    Args:
        app_name: AppleScript application name

    Returns:
        True if browser is Chromium-based, False otherwise
    """
    for config in CHROMIUM_BROWSERS.values():
        if config.app_name == app_name:
            return True
    return False


def get_browser_paths(
    browser_key: str,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Get file paths for a browser.

    Args:
        browser_key: Browser identifier

    Returns:
        Tuple of (data_path, bookmark_path, history_path) or (None, None, None) if not found
    """
    config = get_browser_config(browser_key)
    if not config:
        return None, None, None

    user_dir = os.path.expanduser("~")
    data_path = os.path.join(user_dir, config.data_path)

    if config.is_chromium_based:
        # For Chromium browsers, bookmark and history are in profile directories
        bookmark_path = config.data_path  # Base path, profiles will be added later
        history_path = config.data_path  # Base path, profiles will be added later
    else:
        # For Safari, direct file paths
        bookmark_path = os.path.join(user_dir, config.data_path, config.bookmark_file)
        history_path = os.path.join(user_dir, config.data_path, config.history_file)

    return data_path, bookmark_path, history_path


def get_enabled_browsers(env_checker_func) -> List[Tuple[str, BrowserConfig]]:
    """
    Get list of enabled browsers based on environment variables.

    Args:
        env_checker_func: Function to check if environment variable is enabled (e.g., Tools.getEnvBool)

    Returns:
        List of (browser_key, BrowserConfig) tuples for enabled browsers
    """
    enabled = []
    for browser_key, config in ALL_BROWSERS.items():
        if env_checker_func(config.env_key):
            enabled.append((browser_key, config))
    return enabled


def get_browser_for_tab_switching(browser_key: str) -> Optional[str]:
    """
    Get the AppleScript application name for tab switching.

    Args:
        browser_key: Browser identifier

    Returns:
        AppleScript application name or None if not found
    """
    config = get_browser_config(browser_key)
    return config.app_name if config else None


def get_profile_switch_command(
    browser_key: str, profile_dir: str
) -> Optional[List[str]]:
    """
    Get the command to switch to a specific browser profile.

    Args:
        browser_key: Browser identifier
        profile_dir: Profile directory name

    Returns:
        Command list for subprocess or None if browser doesn't support profiles
    """
    config = get_browser_config(browser_key)
    if not config or not config.supports_profiles:
        return None

    return [
        "open",
        "-na",
        config.app_name,
        "--args",
        f"--profile-directory={profile_dir}",
    ]


# Legacy compatibility - maintain old constants for backward compatibility
CHROMIUM_BROWSER_NAMES = list(CHROMIUM_BROWSERS.keys())
SUPPORTED_BROWSERS = list(ALL_BROWSERS.keys())

# Legacy path mappings for backward compatibility
HISTORY_MAP = {key: config.data_path for key, config in ALL_BROWSERS.items()}
BOOKMARKS_MAP = {key: config.data_path for key, config in ALL_BROWSERS.items()}

# Safari gets special treatment in legacy maps
HISTORY_MAP["safari"] = "Library/Safari/History.db"
BOOKMARKS_MAP["safari"] = "Library/Safari/Bookmarks.plist"
