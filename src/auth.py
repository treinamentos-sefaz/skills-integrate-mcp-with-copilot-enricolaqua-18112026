import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from pathlib import Path


TEACHERS_FILE = Path(__file__).parent / "teachers.json"
ITERATIONS = 600_000


def password_hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS).hex()


def verify_teacher(username: str, password: str) -> bool:
    with TEACHERS_FILE.open(encoding="utf-8") as file:
        teachers = json.load(file)
    if not isinstance(teachers, dict):
        raise ValueError("Teacher credentials must be a JSON object")
    record = teachers.get(username)
    if record is None:
        return False
    salt = bytes.fromhex(record["salt"])
    return hmac.compare_digest(password_hash(password, salt), record["hash"])


def add_teacher(username: str) -> None:
    if not username:
        raise ValueError("Username cannot be empty")
    password = getpass.getpass("Password: ")
    if not password or password != getpass.getpass("Confirm password: "):
        raise ValueError("Password is empty or does not match")
    if TEACHERS_FILE.exists():
        with TEACHERS_FILE.open(encoding="utf-8") as file:
            teachers = json.load(file)
        if not isinstance(teachers, dict):
            raise ValueError("Teacher credentials must be a JSON object")
    else:
        teachers = {}
    if username in teachers:
        raise ValueError("Username already exists")
    salt = secrets.token_bytes(16)
    teachers[username] = {"salt": salt.hex(), "hash": password_hash(password, salt)}
    descriptor = os.open(TEACHERS_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as file:
        json.dump(teachers, file, indent=2)
        file.write("\n")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python auth.py USERNAME")
    add_teacher(sys.argv[1])
