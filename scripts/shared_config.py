"""Load Aimaxhug API credentials.

Priority order:
1. Environment variable AIMAXHUG_API_KEY  (CI / scripting)
2. .env file in project root               (local development)
3. Error — requires the user or administrator to configure the key
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Project root = parent of scripts/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def find_api_key():
    """Return the configured key, or None; never print or write credentials."""
    key = os.environ.get("AIMAXHUG_API_KEY", "").strip()
    if key:
        return key

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").strip().splitlines():
            if line.startswith("AIMAXHUG_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return key
    return None


def load_config() -> dict:
    """Return dict with api_key, or exit with helpful error message."""
    key = find_api_key()
    if key:
        return {"api_key": key}

    print(
        "Error: API key not found.\n\n"
        "Please configure AIMAXHUG_API_KEY in the environment or project .env before running.\n"
        "This script will not create .env, helper scripts, or prompt files.\n\n"
        "Get your API key at: https://api.aimaxhug.cloud\n",
        file=sys.stderr,
    )
    sys.exit(1)
