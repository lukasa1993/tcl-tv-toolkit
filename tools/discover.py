#!/usr/bin/env python3
"""Read an explicitly selected ADB target before root; save identity locally."""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def parse_properties(text):
    return dict(re.findall(r"^\[([^\]\n]+)\]: \[([^\n]*)\]$", text, re.M))


def local_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x") as output:
        path.chmod(0o600)
        json.dump(data, output, indent=2)
        output.write("\n")


def configuration(properties, target, adb, port):
    serial = properties.get("ro.boot.serialno", "")
    fingerprint = properties.get("ro.build.fingerprint", "")
    if not serial or not fingerprint:
        raise ValueError("Missing serial/fingerprint; do not guess target identity")
    config = json.loads((ROOT / "config.example.json").read_text())
    config.update(adb=adb, adb_server_port=port, adb_target=target,
                  expected_serial=serial, expected_fingerprint=fingerprint)
    return config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="Explicit authorized adb serial or ADDRESS:5555")
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--server-port", type=int, default=5037)
    parser.add_argument("--output", type=Path, default=ROOT / ".local/discovery.json")
    parser.add_argument("--write-config", action="store_true", help="Initialize ignored config; refuses overwrite")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT / ".local"):
        parser.error("Discovery output must stay under ignored .local/")
    prefix = [args.adb, "-P", str(args.server_port), "-s", args.target]
    result = subprocess.run(prefix + ["shell", "getprop"], capture_output=True, text=True, timeout=30, check=True)
    properties = parse_properties(result.stdout)
    config = configuration(properties, args.target, args.adb, args.server_port)
    if args.write_config and (ROOT / "config.local.json").exists():
        parser.error("config.local.json already exists; inspect it instead of replacing it")
    local_write(args.output, {"adb_target": args.target, "properties": properties})
    if args.write_config:
        local_write(ROOT / "config.local.json", config)
    print("Saved private discovery. Confirm physical model, full software version and profile compatibility manually.")
    print("Review retained apps and sleep choices in config.local.json before planning any change.")


if __name__ == "__main__":
    main()
