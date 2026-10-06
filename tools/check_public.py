#!/usr/bin/env python3
"""Check Git-tracked publication files; never inspect ignored private files."""
from pathlib import Path
import re
import subprocess
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
BLOCKED_SUFFIXES = {".apk", ".img", ".raw", ".bin", ".plbackup", ".docx", ".pdf", ".sqlite", ".db"}
PATTERNS = {
    "private LAN address": re.compile(rb"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b"),
    "absolute workstation path": re.compile(rb"/" + rb"Users/[A-Za-z0-9_.-]+/"),
    "GitHub token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
}


def violations(path, content):
    errors = []
    parts = Path(path).parts
    if ".local" in parts or "private" in parts or path.endswith(".local.json") or Path(path).suffix in BLOCKED_SUFFIXES:
        errors.append("forbidden private/generated file")
    for name, pattern in PATTERNS.items():
        if pattern.search(content):
            errors.append(name)
    for define in (b"WIFI_SSID", b"WIFI_PASSWORD", b"ACCESS_TOKEN"):
        match = re.search(rb"#define\s+" + define + rb'\s+"([^"]+)"', content)
        if match and not match[1].startswith(b"REPLACE_"):
            errors.append("non-placeholder credential definition")
    return errors


def main():
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    problems = []
    for name in filter(None, files):
        path = ROOT / name
        if path.is_symlink():
            problems.append((name, ["symlink not permitted in publication"]))
            continue
        errors = violations(name, path.read_bytes())
        if path.suffix == ".zip":
            if name != "samples/bootanimation.zip":
                errors.append("unexpected archive")
            else:
                with ZipFile(path) as archive:
                    for entry in archive.namelist():
                        if entry.endswith(".txt"):
                            errors.extend(violations(entry, archive.read(entry)))
                        elif not re.fullmatch(r"part[01]/\d{4}\.png", entry):
                            errors.append("unexpected archive entry")
        if errors:
            problems.append((name, errors))
    for name, errors in problems:
        print(name + ": " + ", ".join(sorted(set(errors))))
    if problems:
        raise SystemExit(1)
    print("Publication check passed for all tracked files. Manually review images and history too.")


if __name__ == "__main__":
    main()
