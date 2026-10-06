# TCL TV Toolkit

Community-oriented notes and tools for inspecting, rooting and configuring a TCL Android / Google TV. Includes an ESP32 Wi-Fi UART bridge with ARM/DISARM and OTA, reversible privacy and app-cleanup plans, Projectivy setup guidance, a local sleep scheduler, and neutral boot-animation samples.

The documented reference platform is **55C6K, T653T01 V643, Android 14, board merak / hardware mt5896**, with Magisk 30.7 and Projectivy 4.71. This is an observed configuration, not a compatibility claim for every TV sold under that model name. Verify the exact build, board, image and slot for your unit.

**Unlocking can erase apps, accounts and settings. Wrong images or bootloader commands can prevent booting.** Read the rooting and recovery notes before interacting with the service port. The default bridge profile only requests `version`; no flashing runs at boot unless explicitly armed.

## Start here

1. Read [rooting and recovery](docs/rooting.md) before attempting root.
2. Copy `config.example.json` to `config.local.json`; enter your own ADB target, serial, exact build fingerprint and retained apps.
3. Authorize ADB on the TV. Use `adb connect <TV_ADDRESS>:5555` if your firmware supports network ADB. Select the same server port and target in the config.
4. Run a read-only audit:

   ```sh
   python3 tools/tv.py audit
   ```

5. Once root is available, build a plan and review it:

   ```sh
   python3 tools/tv.py plan --scopes privacy debloat
   # Optional, more restrictive: add microphones to restrict recording AppOps.
   # Review .local/<timestamp>/plan.json and every command printed above.
   python3 tools/tv.py apply .local/<timestamp>/plan.json --apply
   ```

Applying requires matching the serial, fingerprint and original state. A baseline and guarded rollback script are saved before writes. A plan can be applied once. The tool never reboots, flashes, changes the launcher, starts an app or changes network rules automatically. Verify the resulting settings and a normal reboot yourself; rollback requires working rooted Android.

## Guides

| Guide | Covers |
| --- | --- |
| [Rooting](docs/rooting.md) | Discovery, HDMI service UART, image matching, historical command sequence, reset and recovery |
| [Privacy and cleanup](docs/privacy.md) | Microphone restrictions, recording AppOps, Samba ACR components, optional packages, rollback |
| [Launcher](docs/launcher.md) | Projectivy, favorites, boot/wake app selection, media-service permission, app provenance |
| [Boot artwork](docs/boot-art.md) | Neutral samples, custom frame packaging, memory budgets, early RAW boundaries |
| [Daily sleep](docs/sleep.md) | Fixed UTC offset conversion, private on-TV cron, installation, verification and removal |
| [Lessons](docs/lessons.md) | What failed, what was preserved, and verification limits |
| [ESP32 bridge](esp32/README.md) | Build, wiring, control page, one-shot automation, capture and OTA |

## Neutral sample artwork

![Neutral sample boot artwork](samples/preview.png)

The sample uses geometric blue particles and contains no personal text or logo. Build it, or supply your own `part0` and `part1` frame directories:

```sh
python3 -m pip install -r requirements.txt
python3 tools/boot_art.py
python3 tools/boot_art.py --frames .local/my-frames
```

Outputs go into ignored `.local/sample-art/`: animation ZIP, minimal Magisk module, preview and manifest. The builder never installs anything on a TV. [Artwork guide](docs/boot-art.md) explains installation and validation.

## Local data stays local

Use `config.local.json`, `.local/` and `esp32/private/` for device identity, Wi-Fi credentials, access tokens, captures, rollback state and private artwork. They are ignored by Git. Example configuration contains placeholders. Firmware dumps, APKs, compiled ESP binaries and personal documents are excluded; obtain apps and patch firmware yourself from verified sources.

Ignoring a file does not remove it from existing Git history. This repository starts from clean source files, and `tools/check_public.py` checks tracked files for forbidden paths and common identifiers before publication. Review staged files before pushing any future changes.

## Validation

```sh
python3 -m unittest discover -s tests -v
node esp32/tests/web_ui_test.cjs
c++ -std=c++17 esp32/tests/sequence_test.cpp -o /tmp/tv-sequence-test
/tmp/tv-sequence-test
python3 tools/check_public.py
```

The portable tools are tested with simulated ADB responses; they have not been applied as a new batch to a live TV. The reference procedure was checked on a matching TV, including root, persisted controls, normal boot, and launcher boot/wake behavior. A complete proprietary-network audit, physical microphone disconnection and performance benchmark are outside the evidence collected.

Original toolkit source and neutral samples are licensed under MIT. Third-party apps, firmware and libraries retain their own licenses and are not redistributed here.
