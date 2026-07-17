"""Unit tests for FanPath AI data persistence service."""

import os
import json
import shutil
import pytest
from data_service import sanitize_text, validate_issue_record, load_issues, save_issues, load_crowd_data, save_crowd_data, reset_caches

# Define a temporary test directory root
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(autouse=True)
def run_around_tests():
    """Fixture to back up, clear, and restore json databases for tests."""
    issues_orig = os.path.join(TEST_ROOT, "../issues.json")
    crowd_orig = os.path.join(TEST_ROOT, "../mock_crowd_data.json")
    
    issues_bak = os.path.join(TEST_ROOT, "issues.json.bak")
    crowd_bak = os.path.join(TEST_ROOT, "mock_crowd_data.json.bak")
    
    # Reset in-memory caches to ensure clean isolation
    reset_caches()

    # Back up
    if os.path.exists(issues_orig):
        shutil.copy2(issues_orig, issues_bak)
    if os.path.exists(crowd_orig):
        shutil.copy2(crowd_orig, crowd_bak)
        
    yield
    
    # Restore
    if os.path.exists(issues_bak):
        shutil.copy2(issues_bak, issues_orig)
        os.remove(issues_bak)
    elif os.path.exists(issues_orig):
        os.remove(issues_orig)
        
    if os.path.exists(crowd_bak):
        shutil.copy2(crowd_bak, crowd_orig)
        os.remove(crowd_bak)
    elif os.path.exists(crowd_orig):
        os.remove(crowd_orig)

def test_sanitize_text():
    """Verifies that HTML tags and injection vectors are successfully escaped."""
    assert sanitize_text("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    assert sanitize_text("  hello world  ") == "hello world"
    assert sanitize_text(None) == ""
    assert sanitize_text("safe text 123") == "safe text 123"

def test_validate_issue_record():
    """Verifies that the validation schema fills defaults and cleans fields."""
    raw_issue = {
        "id": "123",
        "reporter_name": "  <script>Name</script>",
        "zone": "Gate A",
        "category": "Safety",
        "description": "Text description...",
        "status": "InvalidStatus"
    }
    
    validated = validate_issue_record(raw_issue)
    assert validated["id"] == "123"
    assert validated["reporter_name"] == "&lt;script&gt;Name&lt;/script&gt;"
    assert validated["status"] == "Open"  # Defaults to Open when invalid
    assert validated["zone"] == "Gate A"

def test_load_and_save_issues():
    """Verifies saving and loading issue lists from the JSON store."""
    app_root = os.path.join(TEST_ROOT, "..")
    mock_issues = [{
        "id": "abc123",
        "reporter_name": "Tester Name",
        "zone": "Food Court",
        "category": "Maintenance",
        "description": "Slippery floor.",
        "timestamp": "2026-07-13 12:00:00",
        "status": "Open"
    }]
    
    save_issues(mock_issues, app_root)
    loaded = load_issues(app_root)
    
    assert len(loaded) == 1
    assert loaded[0]["id"] == "abc123"
    assert loaded[0]["reporter_name"] == "Tester Name"

def test_load_malformed_json_issues():
    """Verifies that malformed or empty database files are handled gracefully without crashing."""
    app_root = os.path.join(TEST_ROOT, "..")
    issues_path = os.path.join(app_root, "issues.json")
    
    # 1. Write an invalid JSON string (dictionary instead of list)
    with open(issues_path, 'w', encoding='utf-8') as f:
        f.write("{'invalid': json}")
        
    # Should fall back to empty list rather than raise exception
    loaded = load_issues(app_root)
    assert isinstance(loaded, list)
    assert len(loaded) == 0

def test_load_and_save_crowd_data():
    """Verifies saving and loading crowd density values."""
    app_root = os.path.join(TEST_ROOT, "..")
    mock_crowd = {
        "Gate A": "High",
        "Gate B": "Low",
        "Food Court": "Medium",
        "Parking": "Low",
        "Main Stand": "High"
    }
    
    save_crowd_data(mock_crowd, app_root)
    loaded = load_crowd_data(app_root)
    
    assert loaded["Gate A"] == "High"
    assert loaded["Gate B"] == "Low"
    assert loaded["Food Court"] == "Medium"

def test_load_malformed_json_crowd():
    """Verifies crowd loader defaults values on malformed files."""
    app_root = os.path.join(TEST_ROOT, "..")
    crowd_path = os.path.join(app_root, "mock_crowd_data.json")
    
    # Write invalid data structure
    with open(crowd_path, 'w', encoding='utf-8') as f:
        f.write("invalid content")
        
    loaded = load_crowd_data(app_root)
    assert isinstance(loaded, dict)
    assert loaded["Gate A"] == "Low"  # Default fallback
