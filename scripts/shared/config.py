"""Load Aimaxhug API credentials.

Priority order:
1. Environment variable AIMAXHUG_API_KEY  (CI / scripting)
2. .env file in project root               (local development)
3. Error — prompts user to create .env file
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
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def load_config() -> dict:
    """Return dict with api_key, or exit with helpful error message."""
    key = os.environ.get("AIMAXHUG_API_KEY", "").strip()
    if key:
        return {"api_key": key}

    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").strip().splitlines():
            if line.startswith("AIMAXHUG_API_KEY="):
                key = line.split("=", 1)[1].strip()
                if key:
                    return {"api_key": key}

    print(
        "Error: API key not found.\n\n"
        "Create .env file in the project root:\n"
        '  echo AIMAXHUG_API_KEY=sk-xxx > .env\n\n'
        "Get your API key at: https://aimaxhug.com\n",
        file=sys.stderr,
    )
    sys.exit(1)
