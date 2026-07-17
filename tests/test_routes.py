"""Integration tests for FanPath AI web routes and error handlers."""

import os
import json
import shutil
import pytest
from app import create_app
import config
import data_service
import gemini_service

# Define test root
TEST_ROOT = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture
def app_instance():
    """Initializes the Flask app in testing mode."""
    # Reset caches for clean test environment
    data_service.reset_caches()
    gemini_service.reset_caches()
    
    app = create_app()
    app.config.update({
        "TESTING": True,
        "DEBUG": False,
        "SECRET_KEY": "test_secret_key_123",
        "RATELIMIT_ENABLED": False  # Disable rate limit for standard route tests
    })
    
    # Back up databases
    issues_orig = os.path.join(TEST_ROOT, "../issues.json")
    crowd_orig = os.path.join(TEST_ROOT, "../mock_crowd_data.json")
    issues_bak = os.path.join(TEST_ROOT, "issues.json.bak")
    crowd_bak = os.path.join(TEST_ROOT, "mock_crowd_data.json.bak")
    
    if os.path.exists(issues_orig):
        shutil.copy2(issues_orig, issues_bak)
    if os.path.exists(crowd_orig):
        shutil.copy2(crowd_orig, crowd_bak)
        
    # Write clean test seeds
    data_service.save_issues([], app.root_path)
    data_service.save_crowd_data({
        "Gate A": "Medium",
        "Gate B": "Low",
        "Food Court": "High",
        "Parking": "Medium",
        "Main Stand": "Low"
    }, app.root_path)
    
    yield app
    
    # Restore databases
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

@pytest.fixture
def client(app_instance):
    """Flask test client instance."""
    return app_instance.test_client()

def test_home_route(client):
    """Verifies the home route renders successfully."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"FanPath AI" in response.data

def test_dashboard_route(client):
    """Verifies the dashboard loads and displays alternates mapping (decision support)."""
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b"Crowd Density" in response.data
    # Check for Alternate suggestion text (decision support)
    assert b"Alternative Food Court" in response.data

def test_transport_route(client):
    """Verifies the transportation & sustainability guide loads successfully."""
    response = client.get('/transport')
    assert response.status_code == 200
    assert b"Transportation" in response.data
    assert b"Sustainability" in response.data
    assert b"Green" in response.data

def test_report_routes(client, app_instance):
    """Verifies issue submissions form works, sanitizes inputs, and redirects."""
    # 1. GET page
    response = client.get('/report')
    assert response.status_code == 200
    assert b"Report a Stadium" in response.data

    # 2. POST report
    form_payload = {
        "reporter_name": "Volunteer <script>XSS</script>",
        "zone": "Gate A",
        "category": "Safety",
        "description": "Exits blocked by banners."
    }
    response = client.post('/report', data=form_payload, follow_redirects=True)
    assert response.status_code == 200
    assert b"reported successfully" in response.data
    
    # Check that database contains sanitized text
    issues = data_service.load_issues(app_instance.root_path)
    assert len(issues) == 1
    assert issues[0]["reporter_name"] == "Volunteer &lt;script&gt;XSS&lt;/script&gt;"
    assert issues[0]["description"] == "Exits blocked by banners."

def test_admin_auth_guard(client):
    """Verifies that accessing `/admin` requires a valid ADMIN_TOKEN query or session."""
    # 1. Access without token -> Should return 403 Forbidden
    response = client.get('/admin')
    assert response.status_code == 403
    assert b"Error 403" in response.data
    
    # 2. Access with invalid token -> Should return 403 Forbidden
    response = client.get('/admin?token=wrong_token')
    assert response.status_code == 403
    
    # 3. Access with valid token -> Should return 200 OK
    token = config.ADMIN_TOKEN
    response = client.get(f'/admin?token={token}')
    assert response.status_code == 200
    assert b"Admin Issue" in response.data

def test_chat_edge_cases(client):
    """Verifies chatbot constraints: very long messages, invalid formats, and errors."""
    # 1. Empty message
    response = client.post('/chat', data=json.dumps({"message": "", "history": []}), content_type='application/json')
    assert response.status_code == 400
    
    # 2. Overlong message (1000+ chars)
    long_msg = "A" * 1005
    response = client.post('/chat', data=json.dumps({"message": long_msg, "history": []}), content_type='application/json')
    assert response.status_code == 400
    assert b"too long" in response.data

def test_rate_limiting(app_instance):
    """Verifies that the rate limiter returns 429 Too Many Requests on route abuse."""
    # Re-enable rate limiting just for this test
    app_instance.config["RATELIMIT_ENABLED"] = True
    client = app_instance.test_client()
    
    # Call endpoint multiple times exceeding limits (15 per minute)
    for _ in range(16):
        response = client.post('/chat', data=json.dumps({"message": "Hi", "history": []}), content_type='application/json')
        
    # The last call should fail with 429 Too Many Requests
    assert response.status_code == 429
    assert b"exceeded your chat rate limit" in response.data
