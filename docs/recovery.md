# Diagnose and recover without repeating blind writes

Start with the last confirmed working stage, last mutation, live screen/LED, uptime if reachable, ESP automation status and all available logs. Distinguish a pending ADB authorization, normal update, wrong network address, UART junk, a boot interruption, module failure and a bad boot image. None of these is established by a black screen alone.

## ESP busy, unreachable or accidentally armed

Use `bridge.py automation` / `status`, then `disarm`. That stops future UART bytes and clears persistent flags; it cannot cancel a TV write already accepted. If control is unavailable, disconnecting ESP power stops its future output, but restarting an armed ESP may resume a stored one-shot. Detach service wiring before a restart intended only to diagnose the ESP. A verified OTA clears ARM and restarts disarmed. Confirm status afterward.

If UART is gibberish, record raw capture and check actual contact numbering, shorts, common ground, direction, voltage, baud and boot timing. Internal loopback tests the ESP UART, not the connector/TV receive path. A good TX path does not prove RX works. Do not use junk text as proof that U-Boot is ready, and do not manufacture success from an ESP log.

## Black screen or stuck logo after an attempt

Check the elapsed time and whether the reviewed sequence is still active before interrupting anything. Stop new transmissions. A deliberate restart during an actual write can worsen the fault; the reference waits were estimates, so use real console/boot evidence where available.

Once the bounded sequence has ended and there is no evidence of a write/update still running, coordinate **one** deliberate normal boot: service connector detached, flash drive out, TV wall power disconnected for ten seconds, then restored; press physical/remote power once if needed and allow up to two minutes. Do not toggle repeatedly. Observe logo/LED and probe the known ADB address without sending a wake key. This procedure restored normal boot after some black states in the original work, but is not a guaranteed rescue.

If the wizard appears, restore setup/network/ADB and verify root as in the runbook. An unlocked message establishes only the displayed unlock state. If Android still fails, keep the last attempt record and use the branches below. A later Enter-only boot-interrupt attempt is a separate deliberate choice, not permission to repeat a full unlock/flash batch.

## Rooted Android works: rollback the actual change

- Privacy/debloat: use the saved `rollback.sh` beside that plan. Review it, push it to a temporary TV path, then run it in an interactive verified root shell. It restores recorded baseline modes, not guessed defaults. Its identity/build/UID-map guards must pass. New apps or changed UIDs need a newly reviewed UID rollback, not removal of the guard.
- Launcher: re-enable the previously active Home package and restore the saved preferred activity and accessibility/AppOps state. Prove Home/Settings before disabling Projectivy. Do not copy a preferred activity from a different device.
- Sample animation: disable module `tv_sample_art` in Magisk; reboot deliberately. Do not remove every module just to undo one known artwork change.
- Scheduler: run `/data/adb/tv-nightly-sleep/disable-scheduler.sh` as root, verify the private daemon stopped and disable any external backup timer too. It does not need a factory reset.

Example plan rollback transport (substitute the actual saved file):

```sh
adb -s YOUR_ADB_TARGET push .local/YOUR_PLAN_DIRECTORY/rollback.sh /data/local/tmp/tv-rollback.sh
adb -s YOUR_ADB_TARGET shell
/debug_ramdisk/su
sh /data/local/tmp/tv-rollback.sh
```

Check restored state and retained functions. A timeout may occur after a mutation succeeded: inspect live state before repeating the command. Rollback scripts require functioning rooted Android and cannot rescue a corrupt bootloader.

## Module-associated startup hang

The 75P8K hung after a broad privacy module and core UID changes. Recovery disabled that module; narrow persisted controls were retained afterward. Do not install that failed design again.

If ADB/root is reachable, inspect `/data/adb/modules/` and each `module.prop`, identify the recently added module and put a `disable` marker in **that module's** directory; reboot deliberately when authorized. Core UID AppOps changes made outside the module need their own baseline restoration. Don't assume disabling a module reverses persisted settings.

The author's [Magisk FAQ](https://topjohnwu.github.io/Magisk/faq.html) describes safe-mode recovery and `magisk --remove-modules`. The latter removes **all modules and automatically reboots**. Prefer a known module's disable marker where possible. If deliberately choosing removal, verify the installed Magisk command/path/version and its help first, record the lost modules and current reboot authorization. [Magisk tools](https://topjohnwu.github.io/Magisk/tools.html) documents the `-n` no-reboot option for removal.

The FAQ's phone volume-key timing is not a confirmed TCL remote/button combination. Do not present it as a guaranteed TV rescue method. The original work recovered the first TV, but did not establish a reusable offline safe-mode button procedure for all TCLs.

## Boot image/layout failure or no rooted Android

An untouched matching stock image is necessary but does not by itself supply a safe way to write it. Establish a readable service console or a build-specific vendor recovery procedure, confirmed destination and available backup before a restore. A factory reset does not necessarily restore a modified boot partition. Do not blindly write `vbmeta`, bootdata, another slot or a whole package as an experiment.

The repository records successful service-UART flashing on two units, not a universal fastboot, recovery-key sequence or serial-read fix. If those prerequisites are missing, report the specific blocker and continue with offline image/log analysis. Do not repeat full writes solely because the last blind attempt showed black. Never relock while a patched image or mismatched verification chain remains installed.
