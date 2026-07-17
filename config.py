"""Configuration module for FanPath AI.

Defines stadium parameters, support languages, decision support redirection maps,
and handles loading security variables from environment configurations.
"""

import os
from dotenv import load_dotenv

# Load environmental configs
load_dotenv()

# App settings
FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "fanpath_ai_secret_key_12345")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "admin_secure_token_123")

# Model configurations
GEMINI_MODEL: str = "gemini-3.1-flash-lite"
GEMINI_CACHE_TIMEOUT_SEC: int = 300  # 5 minutes

# Stadium configuration constants
SUPPORTED_LANGUAGES: list[str] = ["en", "es", "hi"]
STADIUM_ZONES: list[str] = ["Gate A", "Gate B", "Food Court", "Parking", "Main Stand"]

# Decision Support Redirection Map
# Maps heavily crowded areas to their corresponding alternate routes
ALTERNATE_ROUTES: dict[str, str] = {
    "Gate A": "Gate B (South Entrance, Lot 2)",
    "Gate B": "Gate A (North Entrance, Lot 1)",
    "Food Court": "Alternative Food Court at Section 300 or Kiosks at Section 120",
    "Parking": "Overflow Parking Lot E (near Gate C)",
    "Main Stand": "Gate D Corridor / West concourse bypass"
}
