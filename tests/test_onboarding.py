import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "esp32"))
import discover
import firmware
import magisk_bundle
import setup_bridge
import bridge


def image(kernel=b"kernel", ramdisk=b"ramdisk", version=4):
    header = bytearray(4096)
    header[:8] = b"ANDROID!"
    struct.pack_into("<II", header, 8, len(kernel), len(ramdisk))
    struct.pack_into("<I", header, 20, 1584 if version == 4 else 1580)
    struct.pack_into("<I", header, 40, version)
    return bytes(header) + kernel + bytes((-len(kernel)) % 4096) + ramdisk + bytes((-len(ramdisk)) % 4096)


class FirmwareTests(unittest.TestCase):
    def test_header_and_real_content_bounds(self):
        for version in (3, 4):
            info = firmware.image_info(image(version=version))
            self.assertEqual(info["header_version"], version)
            self.assertEqual(info["kernel_sha256"], hashlib.sha256(b"kernel").hexdigest())
        for data in (b"/system/bin/sh: error", image()[:5000], image(version=2), image(kernel=b"")):
            with self.assertRaises(ValueError):
                firmware.image_info(data)

    def test_patch_comparison_protects_kernel_and_rejects_stock(self):
        with tempfile.TemporaryDirectory() as directory:
            stock, patched = Path(directory) / "stock.img", Path(directory) / "patched.img"
            stock.write_bytes(image())
            patched.write_bytes(image(ramdisk=b"patched-ramdisk"))
            self.assertTrue(firmware.compare(stock, patched)["kernel_identical"])
            patched.write_bytes(image(kernel=b"different", ramdisk=b"patched"))
            with self.assertRaisesRegex(ValueError, "kernel changed"):
                firmware.compare(stock, patched)
            patched.write_bytes(image())
            with self.assertRaisesRegex(ValueError, "Ramdisk unchanged"):
                firmware.compare(stock, patched)
            patched.write_bytes(image(ramdisk=b"x" * 9000))
            with self.assertRaisesRegex(ValueError, "larger"):
                firmware.compare(stock, patched)

    def test_verified_extraction_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            archive, output = Path(directory) / "firmware.zip", Path(directory) / "stock.img"
            data = image()
            digest = hashlib.sha256(data).hexdigest()
            with ZipFile(archive, "w") as zipfile:
                zipfile.writestr("boot.img", data)
                zipfile.writestr("META-INF/com/android/metadata", "post-software-version-id=TEST\n")
                zipfile.writestr("../unwanted.txt", "do not extract")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                firmware.extract(archive, output, "0" * 64)
            self.assertFalse(output.exists())
            result = firmware.extract(archive, output, digest)
            self.assertEqual(result["image"]["sha256"], digest)
            self.assertIn("TEST", result["ota_metadata"])
            self.assertFalse((Path(directory).parent / "unwanted.txt").exists())
            with self.assertRaises(FileExistsError):
                firmware.extract(archive, output, digest)
            self.assertEqual(output.read_bytes(), data)

    def test_payload_or_ambiguous_archive_is_not_guessed(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "package.zip"
            with ZipFile(archive, "w") as zipfile:
                zipfile.writestr("payload.bin", b"not a direct boot image")
            with self.assertRaisesRegex(ValueError, "exactly one"):
                firmware.extract(archive, Path(directory) / "boot.img", "0" * 64)

    def test_bundle_rejects_wrong_apk_before_creating_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            apk, output = Path(directory) / "wrong.apk", Path(directory) / "patch"
            apk.write_bytes(b"unverified APK")
            with self.assertRaisesRegex(ValueError, "hash"):
                magisk_bundle.prepare(apk, output, "arm64-v8a")
            self.assertFalse(output.exists())


class OnboardingTests(unittest.TestCase):
    def test_discovery_parses_exact_fingerprint_and_requires_identity(self):
        properties = discover.parse_properties("[ro.boot.serialno]: [TEST_SERIAL]\n[ro.build.fingerprint]: [test/device:14/id/inc:user/release-keys]\n[empty]: []\n")
        config = discover.configuration(properties, "TEST_TARGET", "adb", 5040)
        self.assertEqual(config["expected_fingerprint"], properties["ro.build.fingerprint"])
        self.assertEqual(config["adb_target"], "TEST_TARGET")
        self.assertEqual(config["adb_server_port"], 5040)
        with self.assertRaises(ValueError):
            discover.configuration({}, "TEST_TARGET", "adb", 5037)

    def test_discovery_only_reads_and_keeps_evidence_private(self):
        with tempfile.TemporaryDirectory() as directory:
            fake_root = Path(directory).resolve()
            (fake_root / "config.example.json").write_bytes((ROOT / "config.example.json").read_bytes())
            response = type("Response", (), {"stdout": "[ro.boot.serialno]: [TEST_SERIAL]\n[ro.build.fingerprint]: [test/fingerprint]\n"})()
            with patch.object(discover, "ROOT", fake_root), patch.object(discover.subprocess, "run", return_value=response) as run:
                args = ["discover.py", "--target", "TEST_TARGET", "--write-config"]
                with patch.object(sys, "argv", args), contextlib.redirect_stdout(io.StringIO()):
                    discover.main()
                command = run.call_args.args[0]
                self.assertEqual(command, ["adb", "-P", "5037", "-s", "TEST_TARGET", "shell", "getprop"])
                self.assertEqual((fake_root / "config.local.json").stat().st_mode & 0o777, 0o600)
                with patch.object(sys, "argv", args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    discover.main()

    def test_secret_initialization_escaping_matching_token_permissions_and_no_rotation(self):
        with tempfile.TemporaryDirectory() as directory:
            private = Path(directory) / "private"
            setup_bridge.initialize(private, 'test "ssid"', 'a\\quoted"password')
            header = (private / "config.h").read_text()
            token = (private / "access-token").read_text().strip()
            self.assertIn(json.dumps('test "ssid"'), header)
            self.assertIn(json.dumps('a\\quoted"password'), header)
            self.assertEqual(len(token), 64)
            self.assertIn(token, header)
            self.assertEqual(private.stat().st_mode & 0o777, 0o700)
            for path in private.iterdir():
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                setup_bridge.initialize(private, "new", "new-password")
            self.assertEqual((private / "config.h").read_text(), header)

    def test_invalid_wifi_values_create_no_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "private"
            for ssid, password in (("", "password"), ("a" * 33, "password"), ("ssid", "p\nassword"), ("ssid", "x" * 64)):
                with self.assertRaises(ValueError):
                    setup_bridge.initialize(output, ssid, password)
                self.assertFalse(output.exists())


class BridgeProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = json.loads((ROOT / "examples/bridge-profile.json").read_text())

    def test_dry_default_and_live_requires_ack(self):
        self.assertEqual(bridge.start_fields(self.profile)["mode"], "dry")
        self.assertNotIn("risk", bridge.start_fields(self.profile))
        for mode in ("now", "arm"):
            with self.assertRaisesRegex(ValueError, "authorization"):
                bridge.start_fields(self.profile, mode)
            self.assertEqual(bridge.start_fields(self.profile, mode, True)["risk"], "ack")

    def test_reject_bad_timings_commands_and_incomplete_flash_template(self):
        for key, value in (("start", -1), ("enter", 120001), ("interval", 19), ("settle", 30001), ("start", True)):
            profile = copy.deepcopy(self.profile)
            profile[key] = value
            with self.assertRaises(ValueError):
                bridge.profile_fields(profile)
        for command in ("reset\n", "nonascii-თ", "x" * 257, "YOUR_PATCHED.img"):
            profile = copy.deepcopy(self.profile)
            profile["steps"][0]["command"] = command
            with self.assertRaises(ValueError):
                bridge.profile_fields(profile)
        with self.assertRaises(ValueError):
            bridge.profile_fields(json.loads((ROOT / "examples/unlock-flash-reference.json").read_text()))

    def test_enter_only_and_exact_form_encoding(self):
        profile = json.loads((ROOT / "examples/enter-only-profile.json").read_text())
        fields = bridge.profile_fields(profile)
        self.assertEqual(fields["count"], "0")
        fields = bridge.profile_fields(self.profile)
        self.assertEqual(fields["cmd0"], "version")
        self.assertEqual(fields["wait0"], "2000")
        with tempfile.TemporaryDirectory() as directory:
            fake_root = Path(directory)
            (fake_root / "private").mkdir()
            (fake_root / "private/access-token").write_text("test-token")
            with patch.object(bridge, "ROOT", fake_root), patch.object(bridge.LOCAL_HTTP, "open") as open_request:
                bridge.request("test-host", "/automation/config", bridge.urllib.parse.urlencode(fields).encode(), "application/x-www-form-urlencoded")
                request = open_request.call_args.args[0]
                self.assertEqual(request.get_header("Content-type"), "application/x-www-form-urlencoded")
                self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
                self.assertEqual(bridge.urllib.parse.parse_qs(request.data.decode())["cmd0"], ["version"])


class DocumentationTests(unittest.TestCase):
    def test_relative_markdown_links_resolve_from_each_document(self):
        files = [ROOT / "AGENTS.md", ROOT / "README.md", ROOT / "esp32/README.md", *ROOT.glob("docs/*.md")]
        for file in files:
            for link in re.findall(r"\]\(([^)\s]+)\)", file.read_text()):
                if "://" in link or link.startswith("#"):
                    continue
                target = link.split("#", 1)[0]
                self.assertTrue((file.parent / target).is_file(), f"Broken link {file.name}: {link}")


if __name__ == "__main__":
    unittest.main()
