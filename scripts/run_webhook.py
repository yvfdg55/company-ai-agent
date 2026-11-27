"""Run the real Flask webhook after loading a local .env file."""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv(override=False)
    from app.server import create_app_from_environment

    app = create_app_from_environment()
    app.run(host=os.getenv("WEBHOOK_HOST", "127.0.0.1"), port=int(os.getenv("WEBHOOK_PORT", "5000")))
