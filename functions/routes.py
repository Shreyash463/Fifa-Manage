"""Blueprint route handlers for FanPath AI.

Maps server endpoints, validates token-based authentication on admin views,
manages rate-limited chats, sanitizes user inputs, and handles simulated crowd updates.
"""

import uuid
from datetime import datetime
from typing import Any
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, session, abort, current_app
import config
import data_service
import gemini_service
from extensions import limiter

# Create main blueprint
main_bp = Blueprint('main', __name__)

def check_admin_auth() -> None:
    """Verifies if the client is authenticated via the ADMIN_TOKEN.

    Raises:
        Forbidden HTTP exception (403) if authorization fails.
    """
    # 1. Check if token is in query parameters
    token_param = request.args.get('token')
    if token_param == config.ADMIN_TOKEN:
        session['admin_authenticated'] = True
        return

    # 2. Check if already authenticated in session
    if session.get('admin_authenticated') is True:
        return

    # Fail validation
    abort(403)

@main_bp.route('/')
def home() -> str:
    """Renders the chatbot assistant home page.

    Returns:
        Rendered HTML page string.
    """
    return render_template('home.html')

@main_bp.route('/chat', methods=['POST'])
@limiter.limit("15 per minute")
def chat() -> Any:
    """Handles chat message submissions from visitors.

    Validates payload format, sanitizes query text to prevent XSS,
    and calls the Gemini service.

    Returns:
        JSON response with reply text or error.
    """
    user_data = request.json or {}
    message = user_data.get('message', '')
    history = user_data.get('history', [])

    # Validate message size and type
    if not isinstance(message, str) or not message.strip():
        return jsonify({"reply": "Invalid or empty message. Please try again."}), 400
        
    if len(message) > 1000:
        return jsonify({"reply": "Your message is too long (maximum 1000 characters). Please condense your question."}), 400

    if not isinstance(history, list):
        history = []

    # Sanitize message inputs before calling service
    safe_message = data_service.sanitize_text(message)

    # Call Gemini wrapper
    app_root = current_app.root_path
    reply = gemini_service.call_gemini(safe_message, history)
    
    # Return sanitized reply
    return jsonify({"reply": reply})

@main_bp.route('/dashboard')
def dashboard() -> str:
    """Displays the crowd density dashboard with alternate routing support.

    Returns:
        Rendered HTML dashboard page.
    """
    app_root = current_app.root_path
    crowd_data = data_service.load_crowd_data(app_root)
    
    # Send alternate gate suggestions for real-time decision support
    return render_template(
        'dashboard.html', 
        crowd=crowd_data,
        alternates=config.ALTERNATE_ROUTES
    )

@main_bp.route('/transport')
def transport() -> str:
    """Displays the transit routing guide and sustainability instructions.

    Returns:
        Rendered HTML transportation page.
    """
    return render_template('transport.html')

@main_bp.route('/report', methods=['GET', 'POST'])
def report() -> Any:
    """Handles issue submissions from volunteers and staff.

    GET: Renders reporting form.
    POST: Validates inputs, saves to issues.json database, and redirects.
    """
    app_root = current_app.root_path
    
    if request.method == 'POST':
        reporter_name = request.form.get('reporter_name', 'Anonymous')
        zone = request.form.get('zone', '')
        category = request.form.get('category', 'Other')
        description = request.form.get('description', '')

        # Basic validations
        if not zone or not description:
            flash("Please fill in all required fields (Location and Description).", "danger")
            return redirect(url_for('main.report'))
            
        if len(description) > 500:
            flash("Description text is too long (maximum 500 characters).", "danger")
            return redirect(url_for('main.report'))

        # Rely on database write validation for sanitization to prevent double-escaping
        safe_reporter = reporter_name
        safe_zone = zone
        safe_category = category
        safe_description = description

        # Retrieve and append issue
        issues = data_service.load_issues(app_root)
        new_issue = {
            "id": str(uuid.uuid4())[:8],
            "reporter_name": safe_reporter if safe_reporter else "Anonymous",
            "zone": safe_zone,
            "category": safe_category,
            "description": safe_description,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Open"
        }
        issues.append(new_issue)
        data_service.save_issues(issues, app_root)

        flash("Thank you! The issue has been reported successfully.", "success")
        return redirect(url_for('main.report'))

    return render_template('report.html')

@main_bp.route('/admin')
def admin() -> str:
    """Displays the administrator dashboard guarded by tokens.

    Fails with HTTP 403 if ADMIN_TOKEN is not validated.

    Returns:
        Rendered HTML page for administrators.
    """
    # Force token-based authorization check
    check_admin_auth()
    
    app_root = current_app.root_path
    issues = data_service.load_issues(app_root)
    crowd_data = data_service.load_crowd_data(app_root)
    
    # Check for real-time decision support flag (if any zone is High density)
    has_high_crowd = any(density == "High" for density in crowd_data.values())
    
    # Sort issues so Open ones are on top, and order by timestamp descending
    issues_sorted = sorted(issues, key=lambda x: (x.get('status') != 'Open', x.get('timestamp', '')), reverse=True)
    
    return render_template(
        'admin.html', 
        issues=issues_sorted,
        has_high_crowd=has_high_crowd,
        token=config.ADMIN_TOKEN
    )

@main_bp.route('/admin/resolve/<issue_id>', methods=['POST'])
def resolve_issue(issue_id: str) -> Any:
    """Toggles the status of a specific issue report (Open/Resolved).

    Guarded by token authorization.
    """
    check_admin_auth()
    
    app_root = current_app.root_path
    issues = data_service.load_issues(app_root)
    found = False
    
    for issue in issues:
        if issue.get('id') == issue_id:
            current_status = issue.get('status', 'Open')
            issue['status'] = 'Resolved' if current_status == 'Open' else 'Open'
            found = True
            break

    if found:
        data_service.save_issues(issues, app_root)
        flash(f"Issue #{issue_id} status updated successfully.", "success")
    else:
        flash(f"Issue #{issue_id} not found.", "danger")

    return redirect(url_for('main.admin'))

@main_bp.route('/admin/delete/<issue_id>', methods=['POST'])
def delete_issue(issue_id: str) -> Any:
    """Permanently deletes a specific issue report.

    Guarded by token authorization.
    """
    check_admin_auth()
    
    app_root = current_app.root_path
    issues = data_service.load_issues(app_root)
    original_len = len(issues)
    
    updated_issues = [issue for issue in issues if issue.get('id') != issue_id]
    
    if len(updated_issues) < original_len:
        data_service.save_issues(updated_issues, app_root)
        flash(f"Issue #{issue_id} deleted successfully.", "success")
    else:
        flash(f"Issue #{issue_id} not found.", "danger")

    return redirect(url_for('main.admin'))

@main_bp.route('/api/crowd/update', methods=['POST'])
def update_crowd() -> Any:
    """Simulates crowd shifts by randomizing zone density values.

    Returns:
        JSON response with the new crowd density dictionary.
    """
    import random
    zones = config.STADIUM_ZONES
    densities = ["Low", "Medium", "High"]
    
    new_data = {zone: random.choice(densities) for zone in zones}
    app_root = current_app.root_path
    data_service.save_crowd_data(new_data, app_root)
    
    return jsonify({"status": "success", "data": new_data})
