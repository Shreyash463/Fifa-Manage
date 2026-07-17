"""Data persistence and sanitization service for FanPath AI.

Implements cached file loading/saving logic (reloading only when files change on disk),
safeguards against XSS/injections via HTML escaping, and validates database schemas.
"""

import os
import json
import html
from typing import Any, Union
import config

# In-memory database caches with file modification trackers
_issues_cache: dict[str, Any] = {"data": None, "mtime": 0.0}
_crowd_cache: dict[str, Any] = {"data": None, "mtime": 0.0}

def sanitize_text(text: Union[str, None]) -> str:
    """Escapes user text inputs to prevent HTML/Javascript injection attacks (XSS).

    Args:
        text: Raw user-submitted string.

    Returns:
        Sanitized, HTML-escaped string.
    ```
    """
    if not text:
        return ""
    # Strip whitespace and escape HTML characters
    cleaned = text.strip()
    return html.escape(cleaned)

def get_file_path(filename: str, app_root: str) -> str:
    """Resolves filesystem paths to handle read-only serverless environments.

    Args:
        filename: Database filename (e.g., 'issues.json').
        app_root: Root directory of the Flask application.

    Returns:
        Absolute path to the writeable database file.
    """
    is_serverless = os.getenv("K_SERVICE") or os.getenv("FUNCTION_TARGET")
    if is_serverless:
        tmp_path = os.path.join('/tmp', filename)
        if not os.path.exists(tmp_path):
            src_path = os.path.join(app_root, filename)
            if os.path.exists(src_path):
                import shutil
                try:
                    shutil.copy2(src_path, tmp_path)
                except Exception as e:
                    print(f"Error copying seed database {filename} to /tmp: {e}")
        return tmp_path
    return os.path.join(app_root, filename)

def validate_issue_record(issue: dict[str, Any]) -> dict[str, str]:
    """Validates and sanitizes a single issue database record.

    Args:
        issue: Raw dictionary representing an issue report.

    Returns:
        A validated, safe dictionary with all required schema fields.
    """
    safe_record = {
        "id": sanitize_text(str(issue.get("id", ""))),
        "reporter_name": sanitize_text(str(issue.get("reporter_name", "Anonymous"))),
        "zone": sanitize_text(str(issue.get("zone", "Other Zone"))),
        "category": sanitize_text(str(issue.get("category", "Other"))),
        "description": sanitize_text(str(issue.get("description", ""))),
        "timestamp": sanitize_text(str(issue.get("timestamp", ""))),
        "status": sanitize_text(str(issue.get("status", "Open")))
    }
    
    # Restrict status fields to valid options
    if safe_record["status"] not in ["Open", "Resolved"]:
        safe_record["status"] = "Open"
        
    return safe_record

def load_issues(app_root: str) -> list[dict[str, str]]:
    """Loads issue reports from disk or returns cached data if the file is unchanged.

    Args:
        app_root: Root directory of the Flask application.

    Returns:
        List of validated and sanitized issue records.
    """
    global _issues_cache
    issues_path = get_file_path('issues.json', app_root)
    
    if not os.path.exists(issues_path):
        try:
            with open(issues_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception:
            pass
        _issues_cache = {"data": [], "mtime": 0.0}
        return []

    try:
        # Check current file modification time
        current_mtime = os.path.getmtime(issues_path)
        
        # Return cache if file has not been modified
        if _issues_cache["data"] is not None and _issues_cache["mtime"] == current_mtime:
            return _issues_cache["data"]
            
        with open(issues_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        # Ensure it's a list, fall back to empty list on malformed files
        if not isinstance(raw_data, list):
            raw_data = []
            
        validated_data = [validate_issue_record(item) for item in raw_data if isinstance(item, dict)]
        _issues_cache = {"data": validated_data, "mtime": current_mtime}
        return validated_data
        
    except Exception as e:
        print(f"Error reading issues.json database: {e}")
        return _issues_cache["data"] if _issues_cache["data"] is not None else []

def save_issues(issues: list[dict[str, Any]], app_root: str) -> None:
    """Saves issue reports to disk and updates the in-memory cache.

    Args:
        issues: List of issue dictionaries to persist.
        app_root: Root directory of the Flask application.
    """
    global _issues_cache
    issues_path = get_file_path('issues.json', app_root)
    
    # Pre-validate and sanitize data before writing
    validated_issues = [validate_issue_record(item) for item in issues]
    
    try:
        with open(issues_path, 'w', encoding='utf-8') as f:
            json.dump(validated_issues, f, indent=2, ensure_ascii=False)
        # Update cache modification time tracker
        mtime = os.path.getmtime(issues_path)
        _issues_cache = {"data": validated_issues, "mtime": mtime}
    except Exception as e:
        print(f"Error persisting issues database: {e}")

def load_crowd_data(app_root: str) -> dict[str, str]:
    """Loads crowd density data from disk or returns cached data if the file is unchanged.

    Args:
        app_root: Root directory of the Flask application.

    Returns:
        Dictionary mapping zones to their validated crowd densities (Low/Medium/High).
    """
    global _crowd_cache
    crowd_path = get_file_path('mock_crowd_data.json', app_root)
    default_data = {zone: "Low" for zone in config.STADIUM_ZONES}
    
    if not os.path.exists(crowd_path):
        try:
            with open(crowd_path, 'w', encoding='utf-8') as f:
                json.dump(default_data, f)
        except Exception:
            pass
        _crowd_cache = {"data": default_data, "mtime": 0.0}
        return default_data

    try:
        current_mtime = os.path.getmtime(crowd_path)
        
        # Return cache if file has not been modified
        if _crowd_cache["data"] is not None and _crowd_cache["mtime"] == current_mtime:
            return _crowd_cache["data"]
            
        with open(crowd_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            
        # Validate schema and drop invalid/malformed entries
        validated_data = {}
        for zone in config.STADIUM_ZONES:
            density = str(raw_data.get(zone, "Low")).strip().capitalize()
            if density not in ["Low", "Medium", "High"]:
                density = "Low"
            validated_data[zone] = density
            
        _crowd_cache = {"data": validated_data, "mtime": current_mtime}
        return validated_data
        
    except Exception as e:
        print(f"Error reading mock_crowd_data.json database: {e}")
        return _crowd_cache["data"] if _crowd_cache["data"] is not None else default_data

def save_crowd_data(data: dict[str, str], app_root: str) -> None:
    """Saves crowd density data to disk and updates the in-memory cache.

    Args:
        data: Map of zones and densities to persist.
        app_root: Root directory of the Flask application.
    """
    global _crowd_cache
    crowd_path = get_file_path('mock_crowd_data.json', app_root)
    
    # Pre-validate before writing
    validated_data = {}
    for zone in config.STADIUM_ZONES:
        density = str(data.get(zone, "Low")).strip().capitalize()
        if density not in ["Low", "Medium", "High"]:
            density = "Low"
        validated_data[zone] = density
        
    try:
        with open(crowd_path, 'w', encoding='utf-8') as f:
            json.dump(validated_data, f, indent=2, ensure_ascii=False)
        mtime = os.path.getmtime(crowd_path)
        _crowd_cache = {"data": validated_data, "mtime": mtime}
    except Exception as e:
        print(f"Error persisting crowd density database: {e}")

def reset_caches() -> None:
    """Resets the in-memory database caches (useful for testing)."""
    global _issues_cache, _crowd_cache
    _issues_cache = {"data": None, "mtime": 0.0}
    _crowd_cache = {"data": None, "mtime": 0.0}
