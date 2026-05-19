"""One-time Google OAuth flow for the Sheets API.

Steps:
  1. Create a Desktop app OAuth client in Google Cloud Console:
     https://console.cloud.google.com/apis/credentials
  2. Download client_secrets.json into ./secrets/
  3. Run: python scripts/bootstrap_oauth.py
  4. A browser will open; complete consent. token.json is written.

The backend uses the cached refresh token thereafter.
"""

from __future__ import annotations

import os
import sys

# Make the project root importable.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from backend.app.config import get_settings  # noqa: E402
from backend.app.services.sheets_client import SCOPES  # noqa: E402


def main() -> int:
    settings = get_settings()
    secrets_file = settings.google_client_secrets_file
    token_file = settings.google_token_file

    if not os.path.exists(secrets_file):
        print(f"Missing {secrets_file}.", file=sys.stderr)
        print(
            "Create a Desktop OAuth client at "
            "https://console.cloud.google.com/apis/credentials and download "
            "the JSON to that path.",
            file=sys.stderr,
        )
        return 1

    flow = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
    creds = flow.run_local_server(port=0)
    os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
    with open(token_file, "w") as f:
        f.write(creds.to_json())
    print(f"Saved {token_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
