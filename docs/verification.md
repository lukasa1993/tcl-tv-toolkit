# Evidence checklist before calling the setup complete

Use the exact target and ADB server from local config. These snippets use placeholders; include `-P` when applicable. Save output in `.local/`, not a public issue or commit. Keep the previous baseline and rollback next to the results. A skipped or pending item is not a pass.

## Root and normal boot

Read identity again, confirm it matches config, `sys.boot_completed=1`, selected slot, expected firmware and actual root via `su -c id`. Record SELinux (`getenforce`), `ro.boot.vbmeta.device_state`, `ro.boot.verifiedbootstate`, `ro.boot.flash.locked`, `ro.boot.veritymode` and the Magisk app/daemon version. Reference state was UID 0, Enforcing, unlocked/orange. Root is available without making SELinux permissive.

Verify a deliberate normal reboot with service cable/flash drive removed and ESP disarmed. Allow time for Android startup, then recheck identity/root. A stock/patched hash or ESP TX log alone is not this proof.

## Microphones, ACR and cleanup

```sh
adb -s YOUR_ADB_TARGET shell dumpsys user
adb -s YOUR_ADB_TARGET shell dumpsys audio
adb -s YOUR_ADB_TARGET shell dumpsys package com.tcl.ttvs
adb -s YOUR_ADB_TARGET shell dumpsys activity services com.tcl.ttvs
adb -s YOUR_ADB_TARGET shell settings get global tcl_app_ssm_switch
adb -s YOUR_ADB_TARGET shell settings get global tcl_app_ssm_cidclient_start
adb -s YOUR_ADB_TARGET shell settings get secure assistant
adb -s YOUR_ADB_TARGET shell pm list packages -d --user 0
adb -s YOUR_ADB_TARGET shell pm list packages -U --user 0
```

Check user-0 `no_unmute_microphone` in base/effective restrictions and actual audio mute (`FromRestrictions`/system mute); check hardware-switch state separately when present. Confirm every planned global sharing/hotword flag, cleared secure voice service, component override and absence of the targeted Samba service. Absent data is unknown, not proof of denial.

If the microphones scope was requested, run `cmd appops get <actual-UID>` in a verified root shell for each retained/new app and shell UID 2000. Check all five recording operations are `ignore`; confirm core/shared UIDs were preserved. Don't apply the previous app UID to a reinstalled app. Check logs/plan for partial failures and skipped components. Repeat these checks after the normal reboot, and again after later app installations or firmware changes.

These checks show persisted software controls. They do not prove physical microphone disconnection or that all proprietary telemetry is blocked. Voice search/input may intentionally fail if recording is denied.

## Home, startup and retained functions

```sh
adb -s YOUR_ADB_TARGET shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME
adb -s YOUR_ADB_TARGET shell settings get secure enabled_accessibility_services
adb -s YOUR_ADB_TARGET shell dumpsys accessibility
adb -s YOUR_ADB_TARGET shell cmd appops get com.spocky.projengmenu AUTO_START
```

Confirm Projectivy resolves as Home, its accessibility service is actually bound if startup/wake is requested, and exactly the selected app opens after **boot and wake**. A serialized accessibility setting alone doesn't prove binding. Keep Settings reachable. Open other retained apps manually and verify they do not later take the foreground unexpectedly. Check favorites names/icons/order and selected input rows.

Have the owner verify real YouTube playback with sound, Plex **own-library** playback where requested, other retained apps' playback/login and connected HDMI picture/audio/input switching. Confirm network reconnection and time/date. Opening an app or seeing its thumbnail isn't a playback test. Record any DRM/root incompatibility rather than masking it with speculative system changes.

## Optional artwork and sleep

Artwork: inspect module entries/property, original backup, frame dimensions/decoded budget and preview exit/memory. After installation confirm actual normal reboot and appearance. Early RAW: compare original/replacement hashes, file manifest, owner/mode/context/timestamps, read-only protection, unchanged verification metadata and actual display. The public sample has not itself been hardware-tested.

Sleep: read private crontab, PID command line, `TZ=UTC` daemon environment and startup hook; run action `--test`, inspect its identity/awake/time checks. Verify daemon persistence after reboot. A manual sleep key test changes TV power state; coordinate it, and do not send a power toggle to "check" the result. Finally inspect `actions.log` after a real scheduled event. Until that occurs, report it as pending.

## Handoff acceptance

Record pass/fail/not-tested for every requested item in `.local/session.json`, with evidence paths and observation times. Keep stock image/hash, patched hash/log, local config, plan baselines/rollback, Projectivy export, optional scheduler removal instructions and last attempt record. Record pending account/library work and known recovery limits. Leave ESP disarmed. Only publish anonymized technical knowledge, never the private session itself.
