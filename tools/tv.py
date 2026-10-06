#!/usr/bin/env python3
"""Read-only audit and reviewed, reversible Android configuration plans."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def write_private(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(data, indent=2) + "\n")
    path.chmod(0o600)


class TV:
    def __init__(self, config):
        self.config = config
        for key in ("adb_target", "expected_serial", "expected_fingerprint"):
            value = config.get(key, "")
            if not value or "REPLACE" in value or "TV_ADDRESS" in value:
                raise ValueError(f"Configure {key} in your ignored local config first")
        self.prefix = [config.get("adb", "adb"), "-P", str(config.get("adb_server_port", 5037)),
                       "-s", config["adb_target"]]

    def shell(self, command, root=False):
        args = ["shell", command]
        if root:
            args = ["shell", self.config.get("su", "/debug_ramdisk/su"), "-c", shlex.quote(command)]
        result = subprocess.run(self.prefix + args, capture_output=True, text=True, timeout=90)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "ADB failed")
        return result.stdout.strip()

    def guard(self, root=False):
        serial = self.shell("getprop ro.boot.serialno")
        fingerprint = self.shell("getprop ro.build.fingerprint")
        if (serial, fingerprint) != (self.config["expected_serial"], self.config["expected_fingerprint"]):
            raise RuntimeError("Target serial or build fingerprint does not match local config")
        if self.shell("getprop sys.boot_completed") != "1":
            raise RuntimeError("Android has not finished booting")
        if root and "uid=0(root)" not in self.shell("id", root=True):
            raise RuntimeError("Root permission is required")
        return {"serial": serial, "fingerprint": fingerprint}


def package_state(dump):
    match = re.search(r"^\s*User 0:.*?\benabled=(\d+)\b", dump, re.M)
    if not match:
        raise ValueError("Cannot parse user 0 package state; refusing to guess")
    state = int(match[1])
    if state not in range(5):
        raise ValueError("Unknown package enabled state")
    return state


def component_state(dump, package, component):
    # Only inspect this package's user-0 override lists, not resolver table entries.
    start = re.search(r"^\s*User 0:.*?\benabled=\d+.*$", dump, re.M)
    if not start:
        raise ValueError("Cannot locate package user 0 overrides")
    block = re.split(r"\n\s*User [1-9]\d*:", dump[start.end():], maxsplit=1)[0]
    short = component[len(package):] if component.startswith(package + ".") else component
    for label, state in (("disabledComponents", 2), ("enabledComponents", 1)):
        match = re.search(r"^([ \t]*)" + label + r":[ \t]*$", block, re.M)
        if match:
            entries = set()
            for line in block[match.end():].splitlines():
                if not line.strip():
                    continue
                if len(line) - len(line.lstrip()) <= len(match[1]):
                    break
                entries.add(line.strip())
            if component in entries or short in entries:
                return state
    return 0


def restore_package(state, name):
    verbs = {0: "default-state", 1: "enable", 2: "disable", 3: "disable-user", 4: "disable-until-used"}
    return f"pm {verbs[state]} --user 0 {shlex.quote(name)}"


def restriction_state(users):
    match = re.search(r"UserInfo\{0:.*?(?=UserInfo\{|\nDevice properties:|\Z)", users, re.S)
    if not match:
        raise ValueError("Cannot locate user 0 restrictions")
    base = re.search(r"\n\s+Restrictions:\s*\n(.*?)(?=\n\s+Device policy restrictions:)", match[0], re.S)
    if not base:
        raise ValueError("Cannot parse user 0 base restrictions")
    return int("no_unmute_microphone" in base[1])


def semantic_value(label, check, raw):
    """Compare configuration state, excluding timestamps and runtime counters."""
    if check == "dumpsys user":
        return str(restriction_state(raw))
    if check.startswith("dumpsys package "):
        if "/" in label:
            package, component = label.split("/", 1)
            return str(component_state(raw, package, component))
        return str(package_state(raw))
    if check.startswith("cmd appops get "):
        op = label.split(":", 1)[1]
        match = re.search(r"\b" + re.escape(op) + r":\s*(\w+)", raw)
        return match[1] if match else "default"
    return raw


def build_plan(tv, profile, scopes):
    identity = tv.guard(root=True)
    packages = tv.shell("pm list packages -U --user 0", True)
    installed = dict((name, int(uid)) for name, uid in re.findall(r"package:(\S+) uid:(\d+)", packages))
    changes, skipped = [], []
    dumps, captures = {}, {}

    def change(label, check, before, after, undo):
        captures[check] = before
        changes.append(dict(label=label, check=check, before=semantic_value(label, check, before), after=after, undo=undo))

    if "privacy" in scopes:
        users = tv.shell("dumpsys user", True)
        old = restriction_state(users)
        change("microphone restriction", "dumpsys user", users,
               "pm set-user-restriction --user 0 no_unmute_microphone 1",
               f"pm set-user-restriction --user 0 no_unmute_microphone {old}")
        for namespace, keys in (("global", profile["global_zero"]), ("secure", profile["secure_clear"])):
            for key in keys:
                check = f"settings get {namespace} {shlex.quote(key)}"
                old = tv.shell(check, True)
                undo = f"settings delete {namespace} {key}" if old == "null" else f"settings put {namespace} {key} {shlex.quote(old)}"
                after = f"settings put global {key} 0" if namespace == "global" else f"settings delete secure {key}"
                change(f"{namespace}:{key}", check, old, after, undo)
        for full in profile["disable_components"]:
            package, component = full.split("/", 1)
            if package not in installed:
                skipped.append(f"{full}: package absent")
                continue
            dump = dumps.setdefault(package, tv.shell(f"dumpsys package {package}", True))
            # A fully qualified class must be present, including shortened resolver names.
            short = component[len(package):] if component.startswith(package + ".") else component
            if component not in dump and short not in dump:
                skipped.append(f"{full}: component not found")
                continue
            old = component_state(dump, package, component)
            change(full, f"dumpsys package {package}", dump, f"pm disable --user 0 {full}", restore_package(old, full))
    if "microphones" in scopes:
        # Preserve core/shared Android UIDs. Include the debugging shell explicitly.
        for uid in sorted({uid for uid in installed.values() if uid >= 10000} | {2000}):
            check = f"cmd appops get {uid}"
            before = tv.shell(check, True)
            for op in profile["recording_ops"]:
                match = re.search(r"\b" + re.escape(op) + r":\s*(\w+)", before)
                mode = match[1] if match else "default"
                if mode not in {"allow", "ignore", "deny", "default", "foreground"}:
                    raise ValueError("Unknown AppOp mode")
                change(f"UID {uid}:{op}", check, before,
                       f"cmd appops set {uid} {op} ignore", f"cmd appops set {uid} {op} {mode}")
    if "debloat" in scopes:
        keep = set(tv.config.get("keep_packages", []))
        for package in profile["disable_packages"]:
            uid = installed.get(package)
            if uid is None or uid < 10000 or package in keep:
                skipped.append(f"{package}: absent, core UID or explicitly kept")
                continue
            dump = dumps.setdefault(package, tv.shell(f"dumpsys package {package}", True))
            old = package_state(dump)
            change(package, f"dumpsys package {package}", dump,
                   f"pm disable-user --user 0 {package}", restore_package(old, package))
    return dict(schema=1, identity=identity, scopes=scopes, packages=packages,
                changes=changes, captures=captures, skipped=skipped, applied=False)


def rollback_script(plan):
    q = shlex.quote
    lines = ["#!/system/bin/sh", "set -eu", '[ "$(id -u)" = 0 ]',
             f'[ "$(getprop ro.boot.serialno)" = {q(plan["identity"]["serial"])} ]',
             f'[ "$(getprop ro.build.fingerprint)" = {q(plan["identity"]["fingerprint"])} ]']
    # UIDs can be reused after reinstall. Check the complete installed UID map first.
    digest = hashlib.sha256(plan["packages"].strip().encode()).hexdigest()
    lines += [f'EXPECTED_UID_MAP_HASH={q(digest)}',
              'ACTUAL_UID_MAP_HASH=$(pm list packages -U --user 0 | /data/adb/magisk/busybox awk \'BEGIN { first=1 } { if (!first) printf "\\n"; printf "%s", $0; first=0 }\' | /data/adb/magisk/busybox sha256sum)',
              '[ "${ACTUAL_UID_MAP_HASH%% *}" = "$EXPECTED_UID_MAP_HASH" ] || { echo "Package UID map changed; review rollback manually" >&2; exit 1; }']
    lines.extend(change["undo"] for change in reversed(plan["changes"]))
    lines.append("cmd appops write-settings")
    return "\n".join(lines) + "\n"


def apply_plan(tv, plan, output):
    if plan.get("applied"):
        raise RuntimeError("This plan was already applied; create a fresh plan")
    if tv.guard(root=True) != plan["identity"]:
        raise RuntimeError("Plan belongs to a different target")
    if tv.shell("pm list packages -U --user 0", True) != plan["packages"]:
        raise RuntimeError("Package UID map changed since planning")
    # Check all preconditions before sending any mutating command.
    checks = {}
    for change in plan["changes"]:
        command = change["check"]
        if command not in checks:
            checks[command] = tv.shell(command, True)
        if semantic_value(change["label"], command, checks[command]) != change["before"]:
            raise RuntimeError("Baseline changed since planning; create a fresh plan")
    rollback = output.parent / "rollback.sh"
    rollback.write_text(rollback_script(plan))
    rollback.chmod(0o600)
    plan["applied"] = True
    plan["completed"] = []
    write_private(output, plan)  # Persist baseline and rollback before the first write.
    for index, change in enumerate(plan["changes"]):
        result = tv.shell(change["after"], True)
        if re.search(r"Error:|Exception|Unknown operation|Unknown command", result, re.I):
            raise RuntimeError(f"Command failed at change {index}; use saved rollback")
        plan["completed"].append(index)
        write_private(output, plan)
    tv.shell("cmd appops write-settings", True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.local.json")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit")
    plan = sub.add_parser("plan")
    plan.add_argument("--scopes", nargs="+", choices=["privacy", "microphones", "debloat"], default=["privacy"])
    apply = sub.add_parser("apply")
    apply.add_argument("plan", type=Path)
    apply.add_argument("--apply", action="store_true", required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    tv = TV(config)
    if args.command == "apply":
        path = args.plan.resolve()
        if not path.is_relative_to(ROOT / ".local"):
            raise ValueError("Plans must be under the ignored .local directory")
        apply_plan(tv, json.loads(path.read_text()), path)
        print("Applied. Rollback is saved beside the plan; verify each change and normal boot.")
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output = ROOT / ".local" / stamp
    if args.command == "audit":
        result = {"identity": tv.guard(), "packages": tv.shell("pm list packages -U --user 0"),
                  "audio": tv.shell("dumpsys audio"), "users": tv.shell("dumpsys user"),
                  "home": tv.shell("cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME")}
        write_private(output / "audit.json", result)
        print("Saved read-only audit under .local/" + stamp + "/")
    else:
        result = build_plan(tv, json.loads((ROOT / config["profile"]).read_text()), args.scopes)
        write_private(output / "plan.json", result)
        print(json.dumps({"directory": ".local/" + stamp, "changes": len(result["changes"]), "skipped": result["skipped"]}, indent=2))
        for change in result["changes"]:
            print(change["after"])


if __name__ == "__main__":
    main()
