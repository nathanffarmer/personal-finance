"""One-time interactive Monarch Money login.

Use this when you don't want to put MONARCH_MFA_SECRET in .env. It will
prompt for email, password, and the 6-digit MFA code from your authenticator
app, then save a session pickle that the backend reuses for months.

    python scripts/monarch_login.py
"""

from __future__ import annotations

import asyncio
import getpass
import os
import sys

# Make the project root importable when invoked directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monarchmoney import MonarchMoney, RequireMFAException  # noqa: E402

from backend.app.config import get_settings  # noqa: E402


async def main() -> int:
    settings = get_settings()
    session_path = settings.mm_session_file

    email = settings.monarch_email or input("Monarch email: ").strip()
    password = settings.monarch_password or getpass.getpass("Monarch password: ")

    mm = MonarchMoney()
    try:
        await mm.login(
            email=email,
            password=password,
            use_saved_session=False,
            save_session=False,
        )
    except RequireMFAException:
        code = input("Enter 6-digit MFA code from your authenticator app: ").strip()
        await mm.multi_factor_authenticate(email=email, password=password, code=code)

    os.makedirs(os.path.dirname(session_path) or ".", exist_ok=True)
    mm.save_session(session_path)
    print(f"Session saved to {session_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
