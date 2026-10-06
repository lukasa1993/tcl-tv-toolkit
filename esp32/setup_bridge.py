#!/usr/bin/env python3
"""Create private ESP Wi-Fi configuration and token; does not flash hardware."""
import getpass
import json
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parent


def initialize(directory, ssid, password):
    if not ssid or len(ssid.encode()) > 32 or len(password.encode()) > 63:
        raise ValueError("SSID must contain 1–32 UTF-8 bytes; password at most 63 bytes")
    if any(character in ssid + password for character in "\x00\r\n"):
        raise ValueError("Wi-Fi values cannot contain NUL or line breaks")
    paths = [directory / "config.h", directory / "access-token"]
    if any(path.exists() for path in paths):
        raise FileExistsError("Private config/token already exists; refusing to rotate existing credentials")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    token = secrets.token_hex(32)
    # Literal UTF-8 plus JSON quote/backslash escaping is valid in these C++ strings.
    values = dict(WIFI_SSID=ssid, WIFI_PASSWORD=password, ACCESS_TOKEN=token)
    contents = "#pragma once\n" + "".join(f"#define {key} {json.dumps(value, ensure_ascii=False)}\n" for key, value in values.items())
    created = []
    try:
        for path, content in zip(paths, [contents, token + "\n"]):
            with path.open("x") as output:
                created.append(path)
                path.chmod(0o600)
                output.write(content)
    except Exception:
        for path in created:
            path.unlink()
        raise


def main():
    initialize(ROOT / "private", input("Wi-Fi SSID: "), getpass.getpass("Wi-Fi password (hidden): "))
    print("Created private config and access token. Build next; no credentials are printed.")


if __name__ == "__main__":
    main()
