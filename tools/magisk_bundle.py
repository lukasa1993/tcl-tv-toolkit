#!/usr/bin/env python3
"""Prepare a verified Magisk 30.7 patch/inspection bundle locally; never contact or flash a TV."""
import argparse
import hashlib
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
APK_SHA256 = "e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5"


def prepare(apk, output, abi):
    if hashlib.sha256(apk.read_bytes()).hexdigest() != APK_SHA256:
        raise ValueError("APK does not match the recorded Magisk 30.7 release hash")
    if abi not in {"arm64-v8a", "armeabi-v7a", "x86", "x86_64"}:
        raise ValueError("Unknown Android ABI")
    if output.exists():
        raise FileExistsError("Refusing to replace an existing patch workspace")
    entries = {"boot_patch.sh": "assets/boot_patch.sh", "util_functions.sh": "assets/util_functions.sh",
               "stub.apk": "assets/stub.apk"}
    for binary in ("busybox", "init-ld", "magisk", "magiskboot", "magiskinit"):
        entries[binary] = f"lib/{abi}/lib{binary}.so"
    with ZipFile(apk) as archive:
        for name in entries.values():
            if archive.namelist().count(name) != 1:
                raise ValueError("Missing or ambiguous required Magisk APK entry")
        contents = {name: archive.read(entry) for name, entry in entries.items()}
    output.mkdir(parents=True, mode=0o700)
    for name, content in contents.items():
        path = output / name
        path.write_bytes(content)
        path.chmod(0o600)
    print("Prepared private on-device patch tools. Review docs/firmware.md; nothing installed or flashed.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--abi", required=True, help="Actual target ro.product.cpu.abi, not host architecture")
    parser.add_argument("--output", type=Path, default=ROOT / ".local/magisk-patch")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / ".local"):
        parser.error("Patch tools must stay under ignored .local/")
    prepare(args.apk, args.output, args.abi)


if __name__ == "__main__":
    main()
