import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import tv
import sleep
import boot_art
import check_public

IDENTITY = {"serial": "TEST_SERIAL", "fingerprint": "test/device/build:14/test/test:user/release-keys"}
USERS = "Users:\n  UserInfo{0:Owner:4c13} serialNo=0\n    Restrictions:\n      no_unmute_microphone\n    Device policy restrictions:\n      null\n    Effective restrictions:\n      no_unmute_microphone\n\nDevice properties:\n"
DUMP = "Package test:\n    User 0: installed=true enabled=2\n      disabledComponents:\n        example.pkg.Disabled\n      enabledComponents:\n        example.pkg.Enabled\n    User 10: installed=true enabled=0\n"


class FakeTV:
    def __init__(self):
        self.config = {"keep_packages": ["keep.app"]}
        self.calls = []
        self.responses = {"pm list packages -U --user 0": "package:example.pkg uid:1000\npackage:optional.app uid:10123\npackage:keep.app uid:10124",
                          "dumpsys user": USERS, "dumpsys package example.pkg": DUMP,
                          "dumpsys package optional.app": "User 0: installed=true enabled=2"}
        self.failure = None

    def guard(self, root=False):
        return IDENTITY.copy()

    def shell(self, command, root=False):
        self.calls.append(command)
        if self.failure == command:
            raise RuntimeError("injected connection failure")
        if command in self.responses:
            return self.responses[command]
        if command.startswith("settings get "):
            return "null"
        if command.startswith("cmd appops get "):
            return "RECORD_AUDIO: allow; time=+1m ago"
        return ""


class ConfigurationTests(unittest.TestCase):
    def profile(self):
        return {"global_zero": ["test_global"], "secure_clear": ["test_secure"],
                "recording_ops": ["RECORD_AUDIO"],
                "disable_packages": ["optional.app", "keep.app", "example.pkg", "absent.app"],
                "disable_components": ["example.pkg/example.pkg.Disabled", "example.pkg/example.pkg.Enabled"]}

    def test_component_overrides_are_not_confused(self):
        self.assertEqual(tv.component_state(DUMP, "example.pkg", "example.pkg.Disabled"), 2)
        self.assertEqual(tv.component_state(DUMP, "example.pkg", "example.pkg.Enabled"), 1)
        self.assertEqual(tv.component_state(DUMP, "example.pkg", "example.pkg.Other"), 0)

    def test_plan_is_read_only_and_preserves_original_modes(self):
        fake = FakeTV()
        plan = tv.build_plan(fake, self.profile(), ["privacy", "microphones", "debloat"])
        self.assertFalse(any(command.startswith(("pm disable", "settings put", "cmd appops set")) for command in fake.calls))
        changes = {change["label"]: change for change in plan["changes"]}
        self.assertEqual(changes["microphone restriction"]["undo"], "pm set-user-restriction --user 0 no_unmute_microphone 1")
        self.assertEqual(changes["optional.app"]["undo"], "pm disable --user 0 optional.app")
        self.assertNotIn("keep.app", changes)
        self.assertNotIn("example.pkg", changes)
        self.assertNotIn("UID 1000:RECORD_AUDIO", changes)
        self.assertIn("UID 2000:RECORD_AUDIO", changes)
        self.assertEqual(changes["example.pkg/example.pkg.Enabled"]["undo"], "pm enable --user 0 example.pkg/example.pkg.Enabled")

    def test_precondition_changes_stop_every_write(self):
        fake = FakeTV()
        plan = tv.build_plan(fake, self.profile(), ["debloat"])
        fake.responses["dumpsys package optional.app"] = "User 0: installed=true enabled=0"
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(RuntimeError, "Baseline changed"):
                tv.apply_plan(fake, plan, Path(folder) / "plan.json")
            self.assertFalse((Path(folder) / "rollback.sh").exists())

    def test_runtime_timestamps_are_ignored_but_modes_are_not(self):
        fake = FakeTV()
        plan = tv.build_plan(fake, self.profile(), ["microphones"])
        for uid in (2000, 10123, 10124):
            fake.responses[f"cmd appops get {uid}"] = "RECORD_AUDIO: allow; time=+2m ago"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            tv.apply_plan(fake, plan, path)
            self.assertTrue(path.exists())
            self.assertTrue((path.parent / "rollback.sh").exists())
            with self.assertRaisesRegex(RuntimeError, "already applied"):
                tv.apply_plan(fake, plan, path)

    def test_failure_keeps_prewrite_rollback_and_progress(self):
        fake = FakeTV()
        plan = tv.build_plan(fake, self.profile(), ["privacy"])
        fake.failure = "settings put global test_global 0"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "plan.json"
            with self.assertRaises(RuntimeError):
                tv.apply_plan(fake, plan, path)
            saved = json.loads(path.read_text())
            self.assertEqual(saved["completed"], [0])
            self.assertTrue(saved["applied"])
            script = (path.parent / "rollback.sh").read_text()
            self.assertIn("Package UID map changed", script)

    def test_identity_mismatch_stops_before_root(self):
        config = {"adb_target": "test:5555", "expected_serial": IDENTITY["serial"], "expected_fingerprint": IDENTITY["fingerprint"]}
        actual = tv.TV(config)
        actual.shell = lambda command, root=False: "wrong" if command.endswith("serialno") else IDENTITY["fingerprint"]
        with self.assertRaisesRegex(RuntimeError, "does not match"):
            actual.guard(root=True)

    def test_unknown_parsing_fails_closed(self):
        with self.assertRaises(ValueError):
            tv.package_state("unexpected")
        with self.assertRaises(ValueError):
            tv.restriction_state("unexpected")


class SleepTests(unittest.TestCase):
    def test_fixed_offset_and_day_rollover(self):
        self.assertEqual(sleep.utc_time("01:00", "+04:00"), (21, 0))
        self.assertEqual(sleep.utc_time("23:45", "-05:30"), (5, 15))
        self.assertEqual(sleep.utc_time("00:15", "+05:45"), (18, 30))
        for local, zone in (("24:00", "+00:00"), ("01:00", "+14:01"), ("bad", "UTC")):
            with self.assertRaises(ValueError):
                sleep.utc_time(local, zone)

    def test_generated_scripts_parse_and_never_toggle_power(self):
        files = sleep.generate({"expected_serial": "TEST_SERIAL", "sleep": {"local_time": "01:00", "utc_offset": "+04:00"}})
        self.assertTrue(files["root"].startswith("0 21 * * *"))
        self.assertIn("input keyevent 223", files["sleep-tv.sh"])
        self.assertNotIn("keyevent 26", files["sleep-tv.sh"])
        self.assertIn('TZ=UTC', files["start-scheduler.sh"])
        with tempfile.TemporaryDirectory() as folder:
            for name, content in files.items():
                if name.endswith(".sh"):
                    path = Path(folder) / name
                    path.write_text(content)
                    subprocess.run(["sh", "-n", str(path)], check=True)


class ArtworkAndPublicationTests(unittest.TestCase):
    def test_yuyv_black_and_dimensions(self):
        from PIL import Image
        self.assertEqual(boot_art.yuyv(Image.new("RGB", (2, 1))), bytes([0, 128, 0, 128]))
        with self.assertRaises(ValueError):
            boot_art.yuyv(Image.new("RGB", (3, 1)))

    def test_animation_and_module_contents(self):
        from zipfile import ZipFile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bootanimation.zip"
            parts = [[boot_art.sample_frame(0, 1)], [boot_art.sample_frame(0, 1)]]
            metadata = boot_art.package(parts, path)
            self.assertEqual(metadata["texture"], [640, 180])
            module = path.parent / "module.zip"
            boot_art.module(path, module)
            with ZipFile(path) as z:
                self.assertIsNone(z.testzip())
                self.assertIn(b"p 0 0 part1", z.read("desc.txt"))
            with ZipFile(module) as z:
                self.assertEqual(set(z.namelist()), {"module.prop", "system.prop", "system/media/bootanimation.zip"})

    def test_publication_rejects_secrets_and_private_paths(self):
        self.assertTrue(check_public.violations("esp32/private/config.h", b""))
        self.assertTrue(check_public.violations("public.txt", b"-----BEGIN " + b"PRIVATE KEY-----"))
        self.assertTrue(check_public.violations("public.h", b'#define ACCESS_' + b'TOKEN "secret"'))
        self.assertFalse(check_public.violations("esp32/config.example.h", b'#define ACCESS_TOKEN "REPLACE_WITH_RANDOM_ACCESS_TOKEN"'))


if __name__ == "__main__":
    unittest.main()
