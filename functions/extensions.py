"""Shared extensions module for FanPath AI.

Declares the rate-limiting manager to allow import in both blueprint routes and the app startup config.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure rate limiter by remote client IP address
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "60 per hour"]
)
