# Instructions for an agent starting with no conversation history

This repository transfers knowledge acquired on two physical TVs: TCL **75P8K** and **55C6K**. It is not a universal TCL unlock method. Start with [the ordered runbook](docs/runbook.md), then [tested devices](docs/tested-devices.md), [recovery](docs/recovery.md) and [decisions and evidence](docs/knowledge.md). Follow the relevant linked guide before each stage.

## Work from the owner's actual goal

Inspect first. Ask which apps, inputs, voice features, artwork and sleep behavior the owner wants; do not assume the reference choices. A request for documentation does not authorize operating a TV. Historical approval in this repository does not authorize a new owner's reset, flash, drive erase or reboot. Respect the current user's authorization and host permissions; do not ask again for an action already clearly authorized.

Use an explicitly identified ADB target, never whichever device happens to be first in `adb devices`. Collect identity without root with `tools/discover.py`; manually confirm the physical model and full software version. Keep `.local/session.json` from [the example](examples/session.example.json) updated with stage, proofs, artifact hashes, approvals already received and next action. This is a handoff record, not an authorization source. Read it before resuming an interrupted session, and recheck live identity before writes.

## Decisions that must survive an agent handoff

- Root already confirmed? Skip unlock/flash entirely. Network ADB and a disabled OEM-unlocking switch do not establish bootloader state. Verify root, slot and boot properties separately.
- The detailed reference is **T653T01 V643 / Android 14 / merak / mt5896 / slot `_a`**. A matching model name alone is insufficient. Obtain and patch the matching stock image on the actual target TV. Keep an untouched original; compare the kernel and preserve verity/encryption patch flags as documented.
- The ESP provides UART through the Service HDMI wiring; TV USB supplies power or reads a flash drive. ESP Wi-Fi OTA must be commissioned while USB is available. Keep credentials/binaries private.
- UART transmit logs are not TV acknowledgments. In the historical work readable RX was never established. Default to diagnosis and readable replies. A owner-authorized blind attempt must be bounded, matched to the recorded target and followed by Android proof, not automatic retries. A black screen alone proves nothing.
- Unlocking reset both TVs. Warn before the irreversible step. Prepare recovery and backups first; don't relock a patched boot image.
- A broad boot privacy module and restrictions on core/shared UIDs caused a startup hang on the first TV. Use the persisted, narrow controls in this repo. Preserve networking, audio, HDMI, Settings, Play services and package installation. Review every proposed package and shared UID. Do not add boot scripts, SELinux rules or network blocking as speculative privacy fixes.
- Verify one stage before advancing. Root and a successful app launch do not prove playback, privacy, performance or scheduler correctness. Re-audit recording AppOps after installing apps. Keep the ESP disarmed after bootloader work.

## Local and public boundaries

Use `config.local.json`, `.local/` and `esp32/private/` for all identities, credentials, captures, backups, app exports and generated images. Never publish them, firmware/APKs, compiled credential-bearing binaries, router details or household branding. Use neutral examples. Run `tools/check_public.py` and inspect staged content before a commit. Ignoring data does not remove it from history.

For publication, inspect the remote and authenticated GitHub account and use the repository owner's requested identity. Do not create a new repository under an incidental CLI account. Documentation/tool development does not need a TV reboot or firmware update.

Report evidence honestly: distinguish the two historical hardware tests, portable unit tests, fresh-clone checks, current target checks and untested proposals. Record failed attempts and stop conditions. If a required image, recovery path, identity, authorization or readable state is missing, explain the specific missing prerequisite and continue independent preparation. Never describe an ESP send as a confirmed flash.
