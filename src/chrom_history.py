#!/usr/bin/python3
# -*- coding: utf-8 -*-
import difflib
import glob
import os
import shutil
import sqlite3
import sys
import time
import uuid
from multiprocessing.pool import ThreadPool as Pool
from unicodedata import normalize

from Alfred3 import Items as Items
from Alfred3 import Tools as Tools
from Favicon import Icons
from browsers import get_enabled_browsers, HISTORY_MAP

# Get Browser Histories to load per env (true/false)
HISTORIES = [
    (
        browser_key,
        config.data_path if config.is_chromium_based else HISTORY_MAP[browser_key],
    )
    for browser_key, config in get_enabled_browsers(Tools.getEnvBool)
]

# Get ignored Domains settings
d = Tools.getEnv("ignored_domains", None)
ignored_domains = d.split(",") if d else None

# Show favicon in results or default wf icon
show_favicon = Tools.getEnvBool("show_favicon")

# Determine default search operator (AND/OR)
search_operator_default = Tools.getEnv("search_operator_default", "AND").upper() != "OR"

# if set to true history entries will be sorted
# based on recent visitied otherwise number of visits
sort_recent = Tools.getEnvBool("sort_recent")

# Date format settings
DATE_FMT = Tools.getEnv("date_format", default="%d. %B %Y")


def get_real_profile_name_from_history(browser_path: str, profile_dir: str) -> str:
    """
    Get real profile name from Local State file for history

    Args:
        browser_path (str): Base browser path
        profile_dir (str): Profile directory name (Default, Profile 1, etc.)

    Returns:
        str: Real profile name or fallback to directory name
    """
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if os.path.isfile(local_state_path):
            import json

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


def get_profile_icon_path_from_history(browser_path: str, profile_dir: str) -> str:
    """
    Get profile icon file path from Local State for history

    Args:
        browser_path (str): Base browser path
        profile_dir (str): Profile directory name (Default, Profile 1, etc.)

    Returns:
        str: Profile icon file path or None if not found
    """
    try:
        local_state_path = os.path.join(browser_path, "Local State")
        if os.path.isfile(local_state_path):
            import json

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


def get_profile_name_from_history(path: str) -> str:
    """
    Extract profile name from history path

    Args:
        path (str): Full path to history file

    Returns:
        str: Profile name
    """
    if "Default" in path:
        return "Default"
    elif "Profile" in path:
        return os.path.basename(os.path.dirname(path))
    else:
        return "Safari"


def history_paths() -> list:
    """
    Get valid paths to history from HISTORIES variable (all profiles)

    Returns:
        list: available paths of history files with browser, profile info, and icon path
    """
    user_dir = os.path.expanduser("~")
    valid_hists = list()

    for browser_name, browser_path in HISTORIES:
        if browser_name == "safari":
            # Safari has only one history file
            full_path = os.path.join(user_dir, browser_path)
            if os.path.isfile(full_path):
                valid_hists.append((browser_name, "Safari", full_path, None))
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
                            history_file = os.path.join(profile_dir, "History")
                            if os.path.isfile(history_file):
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
                                ]:
                                    profile_name = get_real_profile_name_from_history(
                                        base_path, profile_dir_name
                                    )
                                    profile_icon_path = (
                                        get_profile_icon_path_from_history(
                                            base_path, profile_dir_name
                                        )
                                    )
                                else:
                                    profile_name = get_profile_name_from_history(
                                        history_file
                                    )
                                    profile_icon_path = None
                                valid_hists.append(
                                    (
                                        browser_name,
                                        profile_name,
                                        history_file,
                                        profile_icon_path,
                                    )
                                )
                                Tools.log(
                                    f"{history_file} → found ({browser_name} - {profile_name})"
                                )
                            else:
                                Tools.log(
                                    f"{history_file} → NOT found ({browser_name} - {profile_dir_name})"
                                )
            else:
                Tools.log(f"{base_path} → NOT found ({browser_name})")

    return valid_hists


def get_histories(dbs: list, query: str) -> list:
    """
    Load History files into list

    Args:
        dbs(list): list with valid history paths with browser and profile info

    Returns:
        list: filters history entries
    """

    results = list()
    with Pool(len(dbs)) as p:  # Exec in ThreadPool
        results = p.map(sql_with_profile, dbs)
    matches = []
    for r in results:
        matches = matches + r
    results = search_in_tuples_with_profile(matches, query)
    # Remove duplicate Entries
    results = removeDuplicates(results)
    # remove ignored domains
    if ignored_domains:
        results = remove_ignored_domains(results, ignored_domains)
    # Sort by element FIRST (before limiting results)
    # For 7-element tuples: (url, title, visit_count, last_visit, browser, profile, icon_path)
    sort_by = 3 if sort_recent else 2  # last_visit or visit_count
    results = Tools.sortListTuple(results, sort_by)  # Sort based on visits or recent
    # Reduce search results to 30 AFTER sorting
    results = results[:30]
    return results


def remove_ignored_domains(results: list, ignored_domains: list) -> list:
    """
    removes results based on domain ignore list

    Args:
        results (list): History results list with tubles
        ignored_domains (list): list of domains to ignore

    Returns:
        list: _description_
    """
    new_results = list()
    if len(ignored_domains) > 0:
        for r in results:
            for i in ignored_domains:
                inner_result = r
                if i in r[0]:
                    inner_result = None
                    break
            if inner_result:
                new_results.append(inner_result)
    else:
        new_results = results
    return new_results


def sql(db: str) -> list:
    """
    Executes SQL depending on History path
    provided in db: str

    Args:
        db (str): Path to History file

    Returns:
        list: result list of dictionaries (Url, Title, VisiCount)
    """
    res = []
    history_db = f"/tmp/{uuid.uuid1()}"
    try:
        shutil.copy2(db, history_db)
        with sqlite3.connect(history_db) as c:
            cursor = c.cursor()
            # SQL satement for Safari
            if "Safari" in db:
                select_statement = f"""
                    SELECT history_items.url, history_visits.title, history_items.visit_count,(history_visits.visit_time + 978307200)
                    FROM history_items
                        INNER JOIN history_visits
                        ON history_visits.history_item = history_items.id
                    WHERE history_items.url IS NOT NULL AND
						history_visits.TITLE IS NOT NULL AND
						history_items.url != '' order by visit_time DESC
                """
            # SQL statement for Chromium Brothers
            else:
                select_statement = f"""
                    SELECT DISTINCT urls.url, urls.title, urls.visit_count, (urls.last_visit_time/1000000 + (strftime('%s', '1601-01-01')))
                    FROM urls, visits
                    WHERE urls.id = visits.url AND
                    urls.title IS NOT NULL AND
                    urls.title != '' order by last_visit_time DESC; """
            Tools.log(select_statement)
            cursor.execute(select_statement)
            r = cursor.fetchall()
            res.extend(r)
        os.remove(history_db)  # Delete History file in /tmp
    except sqlite3.Error as e:
        Tools.log(f"SQL Error: {e}")
        sys.exit(1)
    return res


def sql_with_profile(db_info: tuple) -> list:
    """
    Executes SQL with profile information

    Args:
        db_info (tuple): (browser_name, profile_name, db_path, profile_icon_path)

    Returns:
        list: result list with browser, profile info, and icon path added
    """
    browser_name, profile_name, db_path, profile_icon_path = db_info
    results = sql(db_path)
    # Add browser, profile info, and icon path to each result
    return [
        (
            url,
            title,
            visit_count,
            last_visit,
            browser_name,
            profile_name,
            profile_icon_path,
        )
        for url, title, visit_count, last_visit in results
    ]


def get_search_terms(search: str) -> tuple:
    """
    Explode search term string - now defaults to AND for multiple words

    Args:
        search(str): search term(s), can contain & or | for explicit operators

    Returns:
        tuple: Tuple with search terms
    """
    # Check for explicit operators first
    if "&" in search:
        search_terms = tuple(search.split("&"))
    elif "|" in search:
        search_terms = tuple(search.split("|"))
    else:
        # Default behavior: split by spaces and treat as AND
        search_terms = tuple(search.split())

    search_terms = [normalize("NFC", s) for s in search_terms]
    return search_terms


def removeDuplicates(li: list) -> list:
    """
    Removes Duplicates from history file

    Args:
        li(list): list of history entries

    Returns:
        list: filtered history entries
    """
    if not li:
        return []

    # Check if entries have profile info with icon (7 elements), profile info (6 elements), or not (4 elements)
    if len(li[0]) == 7:
        # With profile info and icon: (url, title, visit_count, last_visit, browser, profile, icon_path)
        unique_entries = {(a, b): (a, b, c, d, e, f, g) for a, b, c, d, e, f, g in li}
    elif len(li[0]) == 6:
        # With profile info: (url, title, visit_count, last_visit, browser, profile)
        unique_entries = {(a, b): (a, b, c, d, e, f) for a, b, c, d, e, f in li}
    else:
        # Without profile info: (url, title, visit_count, last_visit)
        unique_entries = {b: (a, b, c, d) for a, b, c, d in li}

    return list(unique_entries.values())


def search_in_tuples(tuples: list, search: str) -> list:
    """
    Search for search term in list of tuples

    Args:
        tuples(list): List contains tuple to search
        search(str): Search string (multiple words default to AND)

    Returns:
        list: tuple list with result of query string
    """

    def is_in_tuple(tple: tuple, st: str) -> bool:
        match = False
        for e in tple:
            if st.lower() in str(e).lower():
                match = True
        return match

    search_terms = get_search_terms(search)
    result = list()

    for t in tuples:
        # Check for explicit OR operator
        if "|" in search:
            # OR search: any term can match
            if any([is_in_tuple(t, ts) for ts in search_terms]):
                result.append(t)
        elif "&" in search:
            # AND search via &
            if all([is_in_tuple(t, ts) for ts in search_terms]):
                result.append(t)
        else:
            # Default behavior based on setting
            if search_operator_default:
                if all([is_in_tuple(t, ts) for ts in search_terms]):
                    result.append(t)
            else:
                if any([is_in_tuple(t, ts) for ts in search_terms]):
                    result.append(t)

    return result


def search_in_tuples_with_profile(tuples: list, search: str) -> list:
    """
    Search for search term in list of tuples with profile info

    Args:
        tuples(list): List contains tuple to search (url, title, visit_count, last_visit, browser, profile)
        search(str): Search string (multiple words default to AND)

    Returns:
        list: tuple list with result of query string
    """

    def is_in_tuple_with_profile(tple: tuple, st: str) -> bool:
        match = False
        # Search only in url and title (first 2 elements)
        for e in tple[:2]:
            if st.lower() in str(e).lower():
                match = True
        return match

    search_terms = get_search_terms(search)
    result = list()

    for t in tuples:
        # Check for explicit OR operator
        if "|" in search:
            # OR search: any term can match
            if any([is_in_tuple_with_profile(t, ts) for ts in search_terms]):
                result.append(t)
        elif "&" in search:
            # AND search via &
            if all([is_in_tuple_with_profile(t, ts) for ts in search_terms]):
                result.append(t)
        else:
            # Default behavior based on setting
            if search_operator_default:
                if all([is_in_tuple_with_profile(t, ts) for ts in search_terms]):
                    result.append(t)
            else:
                if any([is_in_tuple_with_profile(t, ts) for ts in search_terms]):
                    result.append(t)

    return result


def formatTimeStamp(time_ms: int, fmt: str = "%d. %B %Y") -> str:
    """
    Time Stamp (ms) into formatted date string

    Args:

        time_ms (int):  time in ms from 01/01/1601
        fmt (str, optional): Format of the Date string. Defaults to '%d. %B %Y'.

    Returns:

        str: Formatted Date String
    """
    t_string = time.strftime(fmt, time.gmtime(time_ms))
    return t_string


def main():
    # Get wf cached directory for writing into debugger
    wf_cache_dir = Tools.getCacheDir()
    # Get wf data directory for writing into debugger
    wf_data_dir = Tools.getDataDir()
    # Check and write python version
    Tools.log(f"Cache Dir: {wf_cache_dir}")
    Tools.log(f"Data Dir: {wf_data_dir}")
    Tools.log("PYTHON VERSION:", sys.version)
    if sys.version_info < (3, 7):
        Tools.log("Python version 3.7.0 or higher required!")
        sys.exit(0)

    # Create Workflow items object
    wf = Items()
    search_term = Tools.getArgv(1)
    locked_history_dbs = history_paths()
    # if selected browser(s) in config was not found stop here
    if len(locked_history_dbs) == 0:
        wf.setItem(
            title="Browser History not found!",
            subtitle="Ensure Browser is installed or choose available browser(s) in CONFIGURE WORKFLOW",
            valid=False,
        )
        wf.addItem()
        wf.write()
        sys.exit(0)
    # get search results exit if Nothing was entered in search
    results = list()
    if search_term is not None:
        results = get_histories(locked_history_dbs, search_term)
    else:
        sys.exit(0)
    # if result the write alfred response
    if len(results) > 0:
        # Cache Favicons
        if show_favicon:
            # Convert to format expected by Icons class
            ico_results = [(i[0], i[1]) for i in results]
            ico = Icons(ico_results)
        for i in results:
            url = i[0]
            title = i[1] if i[1] else url.split("/")[2]
            visits = i[2]
            last_visit = formatTimeStamp(i[3], fmt=DATE_FMT)

            # Check if we have profile info
            if len(i) >= 6:
                browser_name = i[4]
                profile_name = i[5]
                profile_icon_path = i[6] if len(i) > 6 else None
                subtitle = f"Last visit: {last_visit} (Visits: {visits})"
            else:
                profile_icon_path = None
                subtitle = f"Last visit: {last_visit} (Visits: {visits})"

            wf.setItem(title=title, subtitle=subtitle, arg=url, quicklookurl=url)
            if show_favicon:
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
            title="Nothing found in History!",
            subtitle=f'Search "{search_term}" in Google?',
            arg=f"https://www.google.com/search?q={search_term}",
        )
        wf.addItem()
    wf.write()


if __name__ == "__main__":
    main()
