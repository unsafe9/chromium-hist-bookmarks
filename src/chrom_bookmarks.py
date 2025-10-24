#!/usr/bin/python3
# -*- coding: utf-8 -*-
import codecs
import glob
import json
import os
import sys
from plistlib import load
from typing import Union

from Alfred3 import Items as Items
from Alfred3 import Tools as Tools
from Favicon import Icons

# Bookmark file path relative to HOME

BOOKMARKS_MAP = {
    "brave": "Library/Application Support/BraveSoftware/Brave-Browser",
    "brave_beta": "Library/Application Support/BraveSoftware/Brave-Browser-Beta",
    "chrome": "Library/Application Support/Google/Chrome",
    "chromium": "Library/Application Support/Chromium",
    "opera": "Library/Application Support/com.operasoftware.Opera",
    "sidekick": "Library/Application Support/Sidekick",
    "vivaldi": "Library/Application Support/Vivaldi",
    "edge": "Library/Application Support/Microsoft Edge",
    "arc": "Library/Application Support/Arc/User Data",
    "dia": "Library/Application Support/Dia/User Data",
    "comet": "Library/Application Support/Comet",
    "safari": "Library/Safari/Bookmarks.plist",
}


# Show favicon in results or default wf icon
show_favicon = Tools.getEnvBool("show_favicon")

# Determine default search operator (AND/OR)
search_operator_default = Tools.getEnv("search_operator_default", "AND").upper() != "OR"

BOOKMARKS = list()
# Get Browser Histories to load based on user configuration
for k in BOOKMARKS_MAP.keys():
    if Tools.getEnvBool(k):
        BOOKMARKS.append((k, BOOKMARKS_MAP.get(k)))


def removeDuplicates(li: list) -> list:
    """
    Removes Duplicates from bookmark file

    Args:
        li(list): list of bookmark entries

    Returns:
        list: filtered bookmark entries
    """
    return list(dict.fromkeys(li))


def get_all_urls(the_json: str) -> list:
    """
    Extract all URLs and title from Bookmark files

    Args:
        the_json (str): All Bookmarks read from file

    Returns:
        list(tuble): List of tublle with Bookmarks url and title
    """

    def extract_data(data: dict):
        if isinstance(data, dict) and data.get("type") == "url":
            urls.append({"name": data.get("name"), "url": data.get("url")})
        if isinstance(data, dict) and data.get("type") == "folder":
            the_children = data.get("children")
            get_container(the_children)

    def get_container(o: Union[list, dict]):
        if isinstance(o, list):
            for i in o:
                extract_data(i)
        if isinstance(o, dict):
            for k, i in o.items():
                extract_data(i)

    urls = list()
    get_container(the_json)
    s_list_dict = sorted(urls, key=lambda k: k["name"], reverse=False)
    ret_list = [(l.get("name"), l.get("url")) for l in s_list_dict]
    return ret_list


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
                real_name = profile_info.get("user_name", profile_dir)
                return real_name
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        Tools.log(f"Error reading Local State: {e}")

    # Fallback to directory name
    return profile_dir


def get_profile_icon_path(browser_path: str, profile_dir: str) -> str:
    """
    Get profile icon file path from Local State

    Args:
        browser_path (str): Base browser path
        profile_dir (str): Profile directory name (Default, Profile 1, etc.)

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
    except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
        Tools.log(f"Error reading profile icon: {e}")

    return None


def get_profile_name(path: str) -> str:
    """
    Extract profile name from path

    Args:
        path (str): Full path to bookmark file

    Returns:
        str: Profile name
    """
    if "Default" in path:
        return "Default"
    elif "Profile" in path:
        return os.path.basename(os.path.dirname(path))
    else:
        return "Safari"


def paths_to_bookmarks() -> list:
    """
    Get all valid bookmarks paths from BOOKMARKS (all profiles)

    Returns:
        list: valid bookmark paths with browser, profile info, and icon path
    """
    user_dir = os.path.expanduser("~")
    valid_bms = list()

    for browser_name, browser_path in BOOKMARKS:
        if browser_name == "safari":
            # Safari has only one bookmark file
            full_path = os.path.join(user_dir, browser_path)
            if os.path.isfile(full_path):
                valid_bms.append((browser_name, "Safari", full_path, None))
                Tools.log(f"{full_path} → found (Safari)")
            else:
                Tools.log(f"{full_path} → NOT found (Safari)")
        else:
            # Chromium-based browsers - check all profiles
            base_path = os.path.join(user_dir, browser_path)
            if os.path.isdir(base_path):
                # Look for Default and Profile* directories
                profile_patterns = ["Default", "Profile*"]
                for pattern in profile_patterns:
                    profile_dirs = glob.glob(os.path.join(base_path, pattern))
                    for profile_dir in profile_dirs:
                        if os.path.isdir(profile_dir):
                            bookmark_file = os.path.join(profile_dir, "Bookmarks")
                            if os.path.isfile(bookmark_file):
                                profile_dir_name = os.path.basename(profile_dir)
                                # Get real profile name and icon for supported browsers
                                if browser_name in [
                                    "edge",
                                    "chrome",
                                    "chromium",
                                    "brave",
                                    "brave_beta",
                                    "opera",
                                    "sidekick",
                                    "vivaldi",
                                    "arc",
                                    "dia",
                                    "comet",
                                ]:
                                    profile_name = get_real_profile_name(
                                        base_path, profile_dir_name
                                    )
                                    profile_icon_path = get_profile_icon_path(
                                        base_path, profile_dir_name
                                    )
                                else:
                                    profile_name = get_profile_name(bookmark_file)
                                    profile_icon_path = None
                                valid_bms.append(
                                    (
                                        browser_name,
                                        profile_name,
                                        bookmark_file,
                                        profile_icon_path,
                                    )
                                )
                                Tools.log(
                                    f"{bookmark_file} → found ({browser_name} - {profile_name})"
                                )
                            else:
                                Tools.log(
                                    f"{bookmark_file} → NOT found ({browser_name} - {profile_dir_name})"
                                )
            else:
                Tools.log(f"{base_path} → NOT found ({browser_name})")

    return valid_bms


def get_json_from_file(file: str) -> json:
    """
    Get Bookmark JSON

    Args:
        file(str): File path to valid bookmark file

    Returns:
        str: JSON of Bookmarks
    """
    return json.load(codecs.open(file, "r", "utf-8-sig"))["roots"]


def extract_safari_bookmarks(bookmark_data, bookmarks_list) -> None:
    """
    Recursively extract bookmarks (title and URL) from Safari bookmarks data.
    Args:
        bookmark_data (list or dict): The Safari bookmarks data, which can be a list or a dictionary.
        bookmarks_list (list): The list to which extracted bookmarks (title and URL) will be appended.
    Returns:
        None
    """
    if isinstance(bookmark_data, list):
        for item in bookmark_data:
            extract_safari_bookmarks(item, bookmarks_list)
    elif isinstance(bookmark_data, dict):
        if "Children" in bookmark_data:
            extract_safari_bookmarks(bookmark_data["Children"], bookmarks_list)
        elif "URLString" in bookmark_data and "URIDictionary" in bookmark_data:
            title = bookmark_data["URIDictionary"].get("title", "Untitled")
            url = bookmark_data["URLString"]
            bookmarks_list.append((title, url))


def get_safari_bookmarks_json(file: str) -> list:
    """
    Get all bookmarks from Safari Bookmark file

    Args:
        file (str): Path to Safari Bookmark file

    Returns:
        list: List of bookmarks (title and URL)

    """
    with open(file, "rb") as fp:
        plist = load(fp)
    bookmarks = []
    extract_safari_bookmarks(plist, bookmarks)
    return bookmarks


def match(search_term: str, results: list) -> list:
    """
    Filters a list of tuples based on a search term.
    Args:
        search_term (str): The term to search for. Can include '&' or '|' to specify AND or OR logic.
        results (list): A list of tuples to search within.
    Returns:
        list: A list of tuples that match the search term based on the specified logic.
    """

    def is_in_tuple(tple: tuple, st: str) -> bool:
        match = False
        for e in tple:
            if st.lower() in str(e).lower():
                match = True
        return match

    result_lst = []
    if "&" in search_term:
        search_terms = search_term.split("&")
        search_operator = "&"
    elif "|" in search_term:
        search_terms = search_term.split("|")
        search_operator = "|"
    else:
        search_terms = search_term.split()
        search_operator = "AND" if search_operator_default else "OR"

    for r in results:
        if search_operator == "&" or search_operator == "AND":
            if all([is_in_tuple(r, ts) for ts in search_terms]):
                result_lst.append(r)
        elif search_operator == "|" or search_operator == "OR":
            if any([is_in_tuple(r, ts) for ts in search_terms]):
                result_lst.append(r)

    return result_lst


def match_with_profile_info(search_term: str, results: list) -> list:
    """
    Filters a list of tuples with profile info based on a search term.
    Args:
        search_term (str): The term to search for. Can include '&' or '|' to specify AND or OR logic.
        results (list): A list of tuples (title, url, browser, profile, icon_path) to search within.
    Returns:
        list: A list of tuples that match the search term based on the specified logic.
    """

    def is_in_tuple_with_profile(tple: tuple, st: str) -> bool:
        match = False
        # Search in title and url only (not browser/profile/icon info)
        for e in tple[:2]:
            if st.lower() in str(e).lower():
                match = True
        return match

    result_lst = []
    if "&" in search_term:
        search_terms = search_term.split("&")
        search_operator = "&"
    elif "|" in search_term:
        search_terms = search_term.split("|")
        search_operator = "|"
    else:
        search_terms = search_term.split()
        search_operator = "AND" if search_operator_default else "OR"

    for r in results:
        if search_operator == "&" or search_operator == "AND":
            if all([is_in_tuple_with_profile(r, ts) for ts in search_terms]):
                result_lst.append(r)
        elif search_operator == "|" or search_operator == "OR":
            if any([is_in_tuple_with_profile(r, ts) for ts in search_terms]):
                result_lst.append(r)

    return result_lst


def main():
    # Log python version
    Tools.log("PYTHON VERSION:", sys.version)
    # check python > 3.7.0
    if sys.version_info < (3, 7):
        Tools.log("Python version 3.7.0 or higher required!")
        sys.exit(0)

    # Workflow item object
    wf = Items()
    query = Tools.getArgv(1) if Tools.getArgv(1) is not None else str()
    bms = paths_to_bookmarks()

    if len(bms) > 0:
        matches = list()
        # Generate list of bookmarks matches the search
        for browser_name, profile_name, bookmarks_file, profile_icon_path in bms:
            if browser_name == "safari":
                bookmarks = get_safari_bookmarks_json(bookmarks_file)
            else:
                bm_json = get_json_from_file(bookmarks_file)
                bookmarks = get_all_urls(bm_json)

            # Add browser, profile info, and icon path to each bookmark
            bookmarks_with_info = [
                (title, url, browser_name, profile_name, profile_icon_path)
                for title, url in bookmarks
            ]
            matched_bookmarks = match_with_profile_info(query, bookmarks_with_info)
            matches.extend(matched_bookmarks)

        # finally remove duplicates from all browser bookmarks
        matches = removeDuplicates(matches)
        # generate list of matches for Favicon download
        ico_matches = []
        if show_favicon:
            ico_matches = [(m[1], m[0]) for m in matches]
        # Heat Favicon Cache
        ico = Icons(ico_matches)
        # generate script filter output
        for m in matches:
            title = m[0]
            url = m[1]
            browser_name = m[2]
            profile_name = m[3]
            profile_icon_path = m[4] if len(m) > 4 else None
            name = title if title else url.split("/")[2]

            # Create subtitle with just URL
            subtitle = f"{url[:60]}..." if len(url) > 60 else url

            wf.setItem(title=name, subtitle=subtitle, arg=url, quicklookurl=url)
            if show_favicon:
                # get favicoon for url
                favicon = ico.get_favion_path(url)
                if favicon:
                    wf.setIcon(favicon, "image")
            else:
                # Use profile icon file when favicon is disabled
                if profile_icon_path and os.path.isfile(profile_icon_path):
                    wf.setIcon(profile_icon_path, "image")
                else:
                    # Fallback to default icon
                    wf.setIcon("icon.png")
            wf.addMod(key="cmd", subtitle="Other Actions...", arg=url)
            wf.addMod(key="alt", subtitle=url, arg=url)
            wf.addItem()
    if wf.getItemsLengths() == 0:
        wf.setItem(
            title="No Bookmark found!",
            subtitle=f'Search "{query}" in Google...',
            arg=f"https://www.google.com/search?q={query}",
        )
        wf.addItem()
    wf.write()


if __name__ == "__main__":
    main()
