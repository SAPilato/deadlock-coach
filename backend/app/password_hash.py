"""Print a password hash for a cloud host (`npm run password-hash`).

You type the password here, on this PC. Only its scrypt hash is printed: paste that into
the host's COACH_PASSWORD_HASH variable. The password itself is never shown or stored.
"""
from __future__ import annotations

import getpass
import sys

from app.auth import MIN_LENGTH, hash_password


def main() -> int:
    password = getpass.getpass(f"Password for the hosted app ({MIN_LENGTH}+ characters): ")
    if len(password) < MIN_LENGTH:
        print(f"Use at least {MIN_LENGTH} characters.")
        return 1
    if getpass.getpass("Type it again: ") != password:
        print("They don't match.")
        return 1
    print("\nSet this as COACH_PASSWORD_HASH on your host (keep it private):\n")
    print(hash_password(password))
    return 0


if __name__ == "__main__":
    sys.exit(main())
