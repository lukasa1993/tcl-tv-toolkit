#!/usr/bin/env python3
"""Inspect/compare Android v3/v4 boot images and extract a hash-verified ZIP boot.img locally."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MAX_IMAGE = 256 * 1024 * 1024


def image_info(data):
    if not 1584 <= len(data) <= MAX_IMAGE or data[:8] != b"ANDROID!":
        raise ValueError("Not a bounded Android boot image; refuse text/error files and unknown formats")
    version = struct.unpack_from("<I", data, 40)[0]
    if version not in (3, 4):
        raise ValueError("Only Android boot header v3/v4 is implemented; investigate other formats separately")
    kernel_size, ramdisk_size = struct.unpack_from("<II", data, 8)
    header_size = struct.unpack_from("<I", data, 20)[0]
    if header_size != (1580 if version == 3 else 1584):
        raise ValueError("Unexpected header size")
    kernel_offset = 4096
    ramdisk_offset = kernel_offset + ((kernel_size + 4095) // 4096) * 4096
    if not kernel_size or not ramdisk_size or ramdisk_offset + ramdisk_size > len(data):
        raise ValueError("Missing/truncated kernel or ramdisk; init_boot-only images need a different workflow")
    if version == 4:
        signature_size = struct.unpack_from("<I", data, 1580)[0]
        signature_offset = ramdisk_offset + ((ramdisk_size + 4095) // 4096) * 4096
        if signature_size and signature_offset + signature_size > len(data):
            raise ValueError("Truncated boot signature")
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "header_version": version,
            "kernel_bytes": kernel_size, "kernel_sha256": hashlib.sha256(data[kernel_offset:kernel_offset + kernel_size]).hexdigest(),
            "ramdisk_bytes": ramdisk_size, "ramdisk_sha256": hashlib.sha256(data[ramdisk_offset:ramdisk_offset + ramdisk_size]).hexdigest()}


def inspect_image(path):
    if path.stat().st_size > MAX_IMAGE:
        raise ValueError("Image exceeds size bound")
    return image_info(path.read_bytes())


def compare(stock, patched):
    original, result = inspect_image(stock), inspect_image(patched)
    if original["header_version"] != result["header_version"] or original["kernel_sha256"] != result["kernel_sha256"]:
        raise ValueError("Header version or raw kernel changed; stop before flashing")
    if original["ramdisk_sha256"] == result["ramdisk_sha256"]:
        raise ValueError("Ramdisk unchanged; this does not establish a Magisk patch")
    if result["bytes"] > original["bytes"]:
        raise ValueError("Patched image larger than stock; independently establish partition capacity")
    return {"stock": original, "patched": result, "kernel_identical": True, "ramdisk_changed": True,
            "note": "Structural checks only: verify Magisk ramdisk flags, firmware match and target slot separately."}


def extract(archive_path, output, expected_sha256):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha256):
        raise ValueError("A complete independently established stock SHA256 is required")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing stock image")
    with ZipFile(archive_path) as archive:
        candidates = [entry for entry in archive.infolist() if entry.filename == "boot.img"]
        if len(candidates) != 1 or candidates[0].file_size > MAX_IMAGE:
            raise ValueError("Need exactly one bounded root-level boot.img; do not guess with payload/incremental packages")
        data = archive.read(candidates[0])  # ZipFile checks CRC; no arbitrary entries are extracted.
        info = image_info(data)
        if info["sha256"] != expected_sha256.lower():
            raise ValueError("Stock SHA256 mismatch; no output written")
        metadata = [entry for entry in archive.infolist() if entry.filename == "META-INF/com/android/metadata"]
        if len(metadata) > 1 or (metadata and metadata[0].file_size > 65536):
            raise ValueError("Ambiguous/oversized OTA metadata")
        ota = archive.read(metadata[0]).decode("utf-8") if metadata else None
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Exclusive creation keeps a known original intact, even if another process creates it meanwhile.
    with output.open("xb") as stream:
        output.chmod(0o600)
        stream.write(data)
    return {"image": info, "ota_metadata": ota}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("image", type=Path)
    unpack = sub.add_parser("extract")
    unpack.add_argument("archive", type=Path)
    unpack.add_argument("--sha256", required=True)
    unpack.add_argument("--output", type=Path, default=ROOT / ".local/firmware/stock-boot.img")
    check = sub.add_parser("compare")
    check.add_argument("stock", type=Path)
    check.add_argument("patched", type=Path)
    args = parser.parse_args()
    if args.command == "extract":
        if not args.output.resolve().is_relative_to(ROOT / ".local"):
            parser.error("Extracted firmware must stay under ignored .local/")
        result = extract(args.archive, args.output, args.sha256)
    elif args.command == "inspect":
        result = inspect_image(args.image)
    else:
        result = compare(args.stock, args.patched)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
