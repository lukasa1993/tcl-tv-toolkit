# Decisions and evidence acquired on the two TVs

Read this alongside [tested devices](tested-devices.md). These are technical findings without household identity or account data. A future agent should keep the reasoning, not just replay commands.

| Observation | Decision for the next owner/agent | Evidence boundary |
| --- | --- | --- |
| USB-only ESP connection powered it but supplied no TV UART | Service wiring is a separate connection; commission OTA before moving it | Direct TV USB-to-computer attempt did not enumerate usable fastboot; other models may differ |
| Service pin mapping worked through ESP TX; receive stayed unreliable | Verify wiring/voltage and seek readable RX; treat blind sends as attempts | Android checks later confirmed root; no TV ACK was obtained from ESP logs |
| Both unlocks led to a setup/account reset | State the reset risk before the gate; preserve originals and local setup notes | Rooting authorization is not retroactive permission for an unannounced reset |
| OEM-unlocking UI stayed disabled after an unlock message | Inspect boot properties, loaded image and actual UID-0 root separately | An OEM toggle or displayed message alone cannot decide outcome |
| Full Magisk setup and its reboot were needed after patch flash | Install the verified full app, complete environment setup, grant root, then verify | A stub app, daemon name or APK installation alone is insufficient |
| V643 source contains direct boot.img and regional metadata differences | Extract only the needed image; compare build/AVB evidence, preserve the discrepancy | Same model/build filename is not a universal compatibility guarantee |
| Broad privacy module plus core UID audio restrictions preceded a boot hang | Use persisted restrictions/components and app/shell recording UIDs; preserve core UIDs | The original failed module is excluded; a shared system UID may power many functions |
| `disable-user` did not give the intended component override | Use `pm disable --user 0` on the specific service/receiver and inspect overrides | Whole-package and individual-component operations are different |
| Targeted Samba/ACR components stayed disabled and service absent after reboot | Keep core TTvs enabled; disable the specific optional paths plus sharing switches | This is software-state evidence, not a packet audit or proof of zero collection |
| Initial privacy changes and network reconnection were followed by YouTube offline symptoms | Test Wi-Fi/Ethernet, time, retained services and actual playback; preserve networking | A app toast alone does not identify the broken dependency or justify blanket DNS blocking |
| Minimal custom Home worked but lacked a usable presentation | Use established Projectivy UI/export, favorites and media channels | Content, favorites IDs, encrypted backups and app-version internals aren't portable |
| Plex initially exposed its own catalog rather than the owner's library | Configure pinned Plex sources and library media rows with the owner | Launcher installation does not authenticate or select a library |
| TCL vendor AUTO_START blocked Projectivy accessibility/startup | Capture baseline, allow only required packages, verify live binding and boot/wake separately | Service-start permission is not selection as the foreground startup app |
| A manually opened Plex test looked like accidental auto-start | Select exactly one Projectivy boot/wake source and test from a known state | Don't diagnose from an app's presence after a manual launch |
| ADB became unreliable during some checks; authorized alternate routing worked | Keep transport/server/target explicit; use existing authorized forwarding if necessary | A timeout doesn't prove a reboot, standby or failed mutation |
| Large decoded boot animation used substantial memory | Budget decoded loop size, preview in a private namespace, sample memory and test normal exit | A preview timeout was not automatically a memory abort; neutral sample is separately generated |
| Early RAW artwork could be replaced with metadata/protection preserved | Treat it as an optional asset change with full backups and a guarded transaction | It doesn't restore verified boot; not a reason to modify bootloader code or AVB metadata |
| Binary backup quoting once saved error text instead of image data | Use exec-out correctly, validate size/header/on-device and host hashes; retain known originals | Filename and successful transport are not binary integrity checks |
| On-TV private cron survived a reboot and sleep key worked | Keep timing/action on the TV, fixed-offset conversion explicit, action sleep-only | The actual first scheduled night event had not yet been observed |
| Optional disabling reduced some running processes | Inspect dependencies and measure the owner's complaint before performance claims | No comparable pre/post speed or playback benchmark was collected |

## Source map and reproducibility

The community [TCL root discussion](https://4pda.to/forum/index.php?showtopic=1080227&st=34540), [boot-art discussion](https://4pda.to/forum/index.php?showtopic=1080227&st=34560) and [Android 14 discussion](https://4pda.to/forum/index.php?showtopic=1080227&st=36640) were historical leads. Full access was limited; they are not substitute evidence for the recorded hardware checks. The full sequence/timing and failed branches are retained in the guides rather than relying on those pages remaining accessible.

The author's [Magisk documentation](https://topjohnwu.github.io/Magisk/install.html), [30.7 release/source](https://github.com/topjohnwu/Magisk/releases/tag/v30.7), and [Projectivy project](https://github.com/spocky/miproja1) document how the actual tools work. Their use does not mean manufacturer telemetry claims were accepted without inspection. The toolkit contains the measured state and explicit limits of the privacy controls.

Every new hardware run should record its model/build, exact artifacts, owner choices, mutation baseline, after-state, normal reboot and recovery observations privately. Add only anonymized technical outcomes to [tested devices](tested-devices.md) after those checks. Unit tests and source inspection must not be promoted to hardware validation. Firmware updates, factory resets and newly installed apps require renewed inspection; "permanent" means persisted under the tested software conditions, not immunity from privileged replacement or physical recording hardware.
