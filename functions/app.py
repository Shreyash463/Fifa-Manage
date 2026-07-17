"""Main server application startup for FanPath AI.

Initializes the Flask app, sets up security headers (Talisman), rate limiting (Limiter),
compression (Compress), registers Blueprint routing, and handles global application error logging.
"""

import os
import logging
import traceback
from flask import Flask, render_template
from flask_talisman import Talisman
from flask_compress import Compress
from extensions import limiter
from routes import main_bp
import config

# Setup standard application logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fanpath.app")

def create_app() -> Flask:
    """Application factory initializing extensions, routing blueprints, and error handlers.

    Returns:
        Fully configured Flask application instance.
    """
    app = Flask(__name__)
    app.secret_key = config.FLASK_SECRET_KEY
    
    # 1. Initialize gzip compression
    Compress(app)

    # 2. Initialize rate limiter
    limiter.init_app(app)

    # 3. Setup Secure HTTP Headers via Talisman
    # Defines strict CSP to permit internal styles, Google Fonts, and FontAwesome icons
    csp = {
        'default-src': [
            "'self'",
            'https://cdnjs.cloudflare.com',
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com'
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            'https://cdnjs.cloudflare.com',
            'https://fonts.googleapis.com'
        ],
        'script-src': [
            "'self'",
            "'unsafe-inline'"
        ],
        'font-src': [
            "'self'",
            'https://cdnjs.cloudflare.com',
            'https://fonts.gstatic.com'
        ],
        'img-src': [
            "'self'",
            'data:'
        ]
    }
    
    Talisman(
        app,
        content_security_policy=csp,
        force_https=False  # Disabled to permit local development over HTTP without redirection loops
    )

    # 4. Register blueprint routing
    app.register_blueprint(main_bp)

    # 5. Generic error handling configurations
    @app.errorhandler(Exception)
    def handle_global_exception(error: Exception) -> tuple[str, int]:
        """Catches all unhandled exceptions, logs details server-side, and serves a generic view.

        Args:
            error: The raised python exception object.

        Returns:
            Tuple with the rendered HTML error page and the matching HTTP status code.
        """
        from werkzeug.exceptions import HTTPException
        
        # 1. Parse standard HTTP exceptions
        if isinstance(error, HTTPException):
            code = error.code if error.code else 500
            description = error.description if error.description else "An unexpected error occurred."
            
            # Custom rate limit error text
            if code == 429:
                description = "You have exceeded your chat rate limit. Please wait a minute before sending more queries."
                
            logger.warning(f"HTTP {code} exception: {description}")
            return render_template('error.html', code=code, description=description), code

        # 2. Server-side log unhandled errors
        logger.error(f"Internal Server Error: {error}", exc_info=True)
        logger.error(traceback.format_exc())
        
        # Return generic screen in production
        return render_template(
            'error.html', 
            code=500, 
            description="A database or processing error occurred. The admin team has been notified."
        ), 500

    return app

# Main entrypoint
app: Flask = create_app()

if __name__ == '__main__':
    # Run locally on port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)
