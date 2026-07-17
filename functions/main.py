from firebase_functions import https_fn
from app import app as flask_app
import os

# Initialize Flask app settings for Cloud Functions environment if needed
@https_fn.on_request()
def fanpath_ai(req: https_fn.Request) -> https_fn.Response:
    # Set host environment flag
    os.environ["K_SERVICE"] = "fanpath-ai"
    
    # Route request to Flask WSGI
    with flask_app.request_context(req.environ):
        return flask_app.full_dispatch_request()
