"""Set the app password used when sharing it (`npm run set-password`).

You type it here, on this PC; it is never shown or sent anywhere. Only a hash is stored.
"""
from __future__ import annotations

import getpass
import sys

from app.auth import MIN_LENGTH, Auth
from app.config import DB_PATH
from app.db import Database


def main() -> int:
    password = getpass.getpass(f"New password ({MIN_LENGTH}+ characters): ")
    if getpass.getpass("Type it again: ") != password:
        print("They don't match. Nothing changed.")
        return 1
    try:
        Auth(Database(DB_PATH)).set_password(password)
    except ValueError as e:
        print(e)
        return 1
    print("Password set. Devices that were logged in must log in again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
