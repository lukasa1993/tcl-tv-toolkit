# Ordered workflow for a new owner and agent

Start at stage 0 with no prior conversation required. Follow only stages the owner requested. Root is a prerequisite for the full privacy/sleep/artwork controls, but ordinary launcher setup can be useful without it. This is a documented route with decision gates, not a promise that every TCL can be rooted. Read [the actual two-device test scope](tested-devices.md) and [recovery](recovery.md) first.

| Stage | Agent can prepare remotely | Owner/device handoff | Required evidence before advancing |
| --- | --- | --- | --- |
| 0–1 | Install tools, inspect an explicit ADB target | Identify TV; enable debugging and approve its key | Model, full build, serial, fingerprint, board, slot and boot state saved |
| 2 | Match package, extract/check stock, prepare patch tools | Patch on the actual TV through Magisk if needed | Untouched stock, own patched image, kernel/ramdisk checks, hashes |
| 3–4 | Build bridge, check HTTP/OTA/loopback, review timeline | Initial USB flash; measure and wire service connector | ESP disarmed, OTA available, wiring verified, RX state recorded |
| 5–6 | Run a reviewed bounded sequence if authorized; verify ADB root | Attach prepared drive, deliberate boot; restore setup and approve root | Normal Android boot, root UID 0, known security state |
| 7–8 | Audit, review/apply scoped plans; inspect Home/service state | Log into retained apps; choose libraries and rows | Privacy persists, Home/Settings and real playback work |
| 9–10 | Generate optional artwork/sleep scripts; check installed state | Artwork/reboot review; observe scheduled event | Stage-specific proofs, rollback retained, no unrequested startup |
| 11 | Collect final evidence and write a local handoff | Confirm retained functions and pending tests | Explicit pass/fail/not-tested report; ESP disarmed |

## 0. Agree scope and prepare the host

Record retained apps/inputs, whether voice recording must be denied, ACR/diagnostics choices, desired startup app and optional artwork/sleep. Do not copy the previous owner's selection. Record current authorization; obtain reset/flash/drive-erase approval only when applicable and not already supplied. Keep Settings reachable throughout.

Prerequisites: Python **3.10+**, Android [Platform Tools/ADB](https://developer.android.com/tools/adb), USB flash drive if using the reference flash route, ESP32-WROOM-32 with USB cable, verified Service connector/breakout, multimeter and an independent USB power supply. UART cannot be supplied by an ESP plugged only into TV USB. Don't cut an optical HDMI cable expecting its video fibers to become UART conductors.

Clone this repository, open a shell at its root, and make the local environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt platformio
adb version
mkdir -p .local
cp examples/session.example.json .local/session.json
```

Python tools themselves use the standard library except the artwork builder's Pillow dependency. PlatformIO is needed only for the ESP. Its [installation documentation](https://docs.platformio.org/en/latest/core/installation/methods/installer-script.html) covers alternative host setups. Keep generated files and accounts local. Update the session after each stage so another agent can resume without guessing.

## 1. Inspect before root

On the TV, open Settings → System/Device Preferences → About, record the complete software version and model label, press the Android build entry seven times, then enable USB debugging in Developer options. Some builds expose ADB on the network; others require different transport. Obtain the address from TV network settings or the owner's router client list. Do not guess a device based only on an address suffix.

```sh
adb connect YOUR_TV_ADDRESS:5555
adb devices -l
# Owner accepts the TV's RSA authorization dialog.
python tools/discover.py --target YOUR_TV_ADDRESS:5555 --write-config
python tools/tv.py audit
```

Use `--server-port`/`--adb` when needed, and reflect them in local config. Discovery is read-only on the TV and refuses to overwrite local evidence/config. Review `.local/discovery.json` and edit `config.local.json`: exact identity, retained apps, appropriate candidate profile and optional schedule. The example profile is **not automatically certified** by discovery. Read the version in Settings if no property clearly supplies the full TCL version.

Inspect `ro.build.fingerprint`, `ro.product.board`, `ro.hardware`, `ro.product.cpu.abi`, `ro.boot.slot_suffix`, `ro.boot.flash.locked`, `ro.boot.vbmeta.device_state`, `ro.boot.verifiedbootstate`, `ro.boot.veritymode` and `sys.boot_completed`; absent properties remain unknown. Save partition names and root-probe results too. Test known `su` paths only as a root probe, with the owner approving the Magisk request if shown. If root already returns UID 0 and normal boot is proven, **skip stages 2–6**. A grey OEM-unlocking switch is not proof of failure or success.

If ADB is unauthorized, wait for the owner to approve its key. If refused/offline, finish the update/boot and verify the address without power toggling. A documented host/router SSH forwarding path can help an authorized network transport, but record it privately and do not assume every router supports one. Use the same ADB server and explicit target consistently.

## 2. Match and prepare firmware

Follow [the complete firmware guide](firmware.md), including the verified V643 source, metadata, stock-image SHA256, on-target Magisk patch, kernel comparison and patch-flag inspection. If the build/layout/AVB evidence differs, investigate a matching route instead of adapting the V643 commands by guesswork. Preserve originals outside the flash drive as well.

Finish with stock + own patched boot images, recorded hashes and exact destination slot. Prepare FAT32 only with permission to erase the identified drive if necessary. A flash drive from another TV is reusable **only after replacing/verifying its device-specific images and filenames**. Its filesystem being compatible does not make its boot image compatible.

## 3. Commission the ESP while USB is available

Follow [ESP commissioning](../esp32/README.md). With the TV serial wires detached, initialize private Wi-Fi/token files, build and upload over computer USB, check authenticated status, open the control page, run loopback, close commissioning, and test OTA with the built application binary while still detached. Verify that the updated bridge returns disarmed. Preserve its private token/config; don't rotate them accidentally between builds.

Check an Enter/diagnostic **dry run** first. Confirm start delay, Enter duration/interval, quiet interval and wait after each command. With independent ESP power, ARM triggers on **ESP restart**. If only the TV will restart, use Start now and tell the owner when the Enter burst has actually started.

## 4. Verify the UART path

Follow [service wiring](rooting.md#service-uart-and-esp): on the observed implementation HDMI 14 → ESP RX25, HDMI 2 → ESP TX26, HDMI 11 → GND, 115200 8N1. Identify contacts by actual plug numbering and continuity, not wire colors or PCB pads. Check shorts unpowered and logic voltage before connection. Use USB power; no HDMI power feed.

Capture with `bridge.py read --follow --save .local/uart.bin`. Try a harmless diagnostic only when the console is actually accessible; do not send U-Boot commands to a normal Android prompt and assume they run. Confirm baud, direction, ground, continuity and boot timing if RX is unreadable. Reversing wires arbitrarily is not a substitute for measurement.

The original two-TV work never achieved reliable readable RX. A new owner may explicitly authorize a blind attempt after matching the target and accepting the reset/boot risk. Record that constraint and use the bounded reference profile, not invented exploratory flash commands. Transmit logs are only host-side evidence.

## 5. Unlock and flash only if required

**Gate:** target/build/slot proven; untouched stock retained; own patched image verified; correct drive/file present; recovery limitations discussed; current owner has accepted reset/flash risk. Do not proceed while an update is running. Do not relock a patched image.

Copy [the historical profile](../examples/unlock-flash-reference.json) into `.local/flash-profile.json`. Replace both placeholders after checking the drive filename and partition; the client rejects unresolved placeholders. Review all eight commands against [the historical sequence](rooting.md#historical-bootloader-sequence). It is not interchangeable with phone fastboot instructions.

```sh
python esp32/bridge.py disarm
python esp32/bridge.py run --profile .local/flash-profile.json
python esp32/bridge.py automation
```

Default mode is **dry**: timeline only, no UART bytes. Wait for completion; disarm before editing or starting another operation. Once all gates are satisfied and the TV is deliberately powered off with drive/service cable ready:

```sh
python esp32/bridge.py run --profile .local/flash-profile.json --mode now --accept-reset-risk
python esp32/bridge.py automation
```

The agent confirms the live Enter burst is running, then tells the owner to power on during the **60-second** burst. The sequence waits two seconds afterward, sends the reviewed commands and waits 60 seconds after the boot write command before reset. Timings are transmission scheduling, not completion acknowledgments. Record attempt time and state; don't automatically repeat. The `--accept-reset-risk` flag cannot replace the owner's authorization.

Alternatively `--mode arm` runs once at the next **ESP** boot. Tell the owner which hardware must restart. Check the flag was consumed before bytes. An [Enter-only profile](../examples/enter-only-profile.json) exists for an explicitly chosen boot-interrupt attempt; it does not flash or prove success. Read [recovery](recovery.md) after a black screen or missing response. Do not turn an Enter-only retry into a full flash replay.

## 6. Restore setup and prove Magisk root

If the wizard appears, the reset happened: restore networking, debugging and ADB authorization. Check the new address and live identity. Reinstall the verified **full** Magisk APK matching the patch, open it, accept its additional-environment-setup reboot when needed, then wait for a normal Android boot. A stub manager or unlock message alone does not prove usable root.

```sh
adb -s YOUR_ADB_TARGET shell getprop sys.boot_completed
adb -s YOUR_ADB_TARGET shell /debug_ramdisk/su -c id
# Owner grants the superuser request if shown; rerun id once if it was pending.
adb -s YOUR_ADB_TARGET shell getenforce
adb -s YOUR_ADB_TARGET shell getprop ro.boot.vbmeta.device_state
adb -s YOUR_ADB_TARGET shell getprop ro.boot.verifiedbootstate
adb -s YOUR_ADB_TARGET shell getprop ro.boot.slot_suffix
python esp32/bridge.py disarm
python tools/tv.py audit
```

Reference proof was `uid=0(root)`, Enforcing, unlocked/orange and `_a`, after the manager setup reboot. On another layout resolve and record the actual `su` path; update config. Keep the full root proof and any boot-image/daemon checks locally. Remove service wiring and flash drive once no longer needed. Do not continue privacy changes while root/normal boot remains unproven.

## 7. Install retained apps and configure Home

Follow [the launcher guide](launcher.md). Obtain Projectivy from its author/app store and install the owner's retained apps. Let the owner perform account login and library selection. Set `keep_packages` to actual package names from the installed package list, including the launcher if it appears in a candidate cleanup list. Configure favorites/order/media rows and connected inputs through the UI, then export Projectivy settings into `.local/`.

Prove Home and Settings before optionally disabling stock home/setup. Choose one startup app, enable and verify accessibility, and save/review vendor `AUTO_START` modes if the reference permission issue appears. An allowance for Plex's service is distinct from choosing Plex as the foreground startup app. Test both deliberate reboot and remote wake. If account work is still pending, record it rather than claiming completion.

## 8. Apply narrow privacy/cleanup controls

Follow [privacy and cleanup](privacy.md), preserving the owner's functions and core/shared UIDs. Do this **after installing apps** so recording restrictions cover their allocated UIDs. Baseline first; start with separate scopes to simplify diagnosis:

```sh
python tools/tv.py plan --scopes privacy
# Inspect the printed commands, skipped entries and .local/<timestamp>/plan.json.
python tools/tv.py apply .local/YOUR_REVIEWED_TIMESTAMP/plan.json --apply
```

Only generate/apply `microphones` if the owner wants recording denied, including voice search. Review `debloat` candidates independently; disable reversibly, don't remove data. A partial application is not automatically retried: inspect saved progress and rollback. After a deliberate normal reboot, repeat microphone, component, flag and retained-function checks in [final verification](verification.md). Never restrict core UIDs to make an AppOps count look complete.

For performance requests, measure the actual complaint, available memory, running service/process state and playback first. Disable optional services only where dependency inspection supports it. No measured benchmark in this repo supports blanket claims about speed, swap tuning or aggressive networking changes.

## 9. Optional boot artwork

Follow [artwork](boot-art.md). Generate/review neutral or owner's frames locally, use a minimal Magisk module, verify original path/property and memory budget, preserve the original, and test a normal reboot. Early static RAW replacement is a separate firmware-specific change requiring partition/metadata backups and a reviewed guarded writer. It is not required for root/privacy/launcher completion. The repo intentionally supplies no universal raw-partition writer.

## 10. Optional on-TV sleep

Follow [sleep](sleep.md). Choose owner's local time/fixed UTC offset; generate, inspect and install the scripts as root. Check target identity, timezone conversion, daemon PID/environment and `--test`. Verify persistence after reboot and an **actual scheduled event** separately. Use key 223 only for sleep; no toggle/wake/relaunch action. Record whether a computer/cloud backup timer also exists so all timers can be disabled later.

## 11. Final verification and handoff

Complete [the evidence checklist](verification.md). Preserve config, baselines, rollback, hashes, app export, scheduler instructions and unresolved tests under `.local/`. Report which requested stages passed, failed or remain untested. State privacy limits and unobserved clock events precisely. Leave ESP disarmed. Do not publish private handoff data with the reusable knowledge.
