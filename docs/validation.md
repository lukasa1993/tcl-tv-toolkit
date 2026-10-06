# Portable onboarding validation

Validation performed on **2026-10-06**, separately from the [two historical hardware runs](tested-devices.md):

- 25 Python tests passed, including read-only discovery, exact identity, private credential creation/escaping, no credential rotation, boot-header bounds, hash-gated extraction, original preservation, patch kernel comparison, dry-default/live-mode handling, form encoding and local documentation links. Existing configuration/rollback/scheduler/artwork tests remained passing.
- Existing C++ sequence tests passed for timing, Enter intervals, dry run, cancellation, no repeat, clock rollover and stalls. The web UI regression passed for Start/Stop and risk acknowledgment behavior.
- A clean copy of all staged public source files was created without the original ignored configuration, credentials or backups. A fresh Python environment installed requirements; all Python tests, CLI help entry points and neutral artwork generation passed there.
- That clean copy initialized dummy private ESP credentials and built the pinned ESP firmware successfully. RAM was 29.7% and application flash 79.7%. No hardware upload or OTA request was sent.
- The Magisk bundle extractor succeeded against the retained, hash-matched 30.7 APK. The new boot-image comparator succeeded against the retained real stock and patched V643 images: both 56,623,104 bytes, v4 header, identical kernel and changed ramdisk.
- Yandex's public metadata and ZIP directory/OTA metadata were inspected using bounded range reads. No new full firmware package download or flash was performed.
- Publication checks passed for tracked public files. Private artifacts and commissioning/build outputs stayed ignored.

These checks do **not** constitute another fresh-clone-to-TV run. New discovery/configuration clients were tested with simulated ADB/HTTP responses; the new same-device patch recipe was checked against Magisk's source and release contents without executing it on a TV. The neutral artwork wasn't installed. Recovery key combinations, a working UART RX fix, universal firmware compatibility and a comprehensive traffic/performance audit remain outside the evidence. The runbook directs the next agent to establish those device-specific prerequisites rather than claim they have already been solved.
