# Tested devices

The underlying procedure was developed and tested on **two physical TCL TVs of different models: 75P8K and 55C6K**. Both were rooted and configured successfully. The first model supplied the initial investigation and recovery lessons; the second exercised the refined configuration. This record includes model names and technical results only. Device identifiers, connection details, captures and private artwork are kept outside the published files.

## Hardware test scope

| Area | TCL 75P8K | TCL 55C6K |
| --- | --- | --- |
| Root | Root access confirmed; normal reboot passed after recovery from the failed privacy module | Magisk 30.7 root confirmed; unlocked/orange state and SELinux Enforcing checked |
| Microphone controls | Persisted user restriction and application recording AppOps checked after reboot; audio reported both hardware-switch and restriction mute | Persisted user restriction and application recording AppOps checked after reboot; restriction/system mute confirmed, hardware-switch mute was not established |
| ACR and diagnostics | Samba service/receiver and Alexa components disabled; Samba service absent; sharing flags checked | Targeted components disabled; states persisted after reboot; Samba service absent and sharing flags checked |
| Optional app cleanup | Reversible package disabling and dependency inspection; the later performance-cleanup batch was not separately verified after reboot | Reversible optional-package disabling, with enabled/disabled states checked after reboot |
| Projectivy | Version 4.71 default Home; Home navigation, cold launcher restart and app/content rows checked | Version 4.71 default Home; minimal favorites and selected-app startup after reboot and remote wake checked |
| Android boot animation | Custom animation installed; native preview and normal reboot verified | Custom animation installed; guarded native preview and normal reboot verified |
| Early static boot image | Targeted RAW replacement; original format/protection preserved, metadata unchanged and normal reboot passed | Targeted RAW replacement; original format/protection preserved, metadata unchanged and normal reboot passed |
| Local sleep schedule | Not part of this model's recorded on-TV scheduler test | Private cron, UTC conversion, action dry run, sleep key and daemon persistence after reboot checked; the first actual scheduled nighttime event had not occurred when documented |

The 55C6K's detailed reference build was **V8-T653T01-LF1V643**, Android 14, reported hardware `mt5896`, board `merak`, active slot `_a`. The public candidate profile and historical bootloader command table are tied to that reference. This page does not claim that the profile, boot image or complete package list is interchangeable between the two models.

## Shared observations and recovery lessons

The service-HDMI/ESP32 route was used during the rooting work on both models. Reliable readable UART replies were not established; subsequent Android root and boot-state checks supplied the confirmation. Unlocking reset setup/accounts. On the 75P8K, an early broad privacy module was followed by a startup hang; recovery disabled it and core shared-UID audio controls were restored. The failed module was excluded from the refined 55C6K procedure and from this repository.

Both models subsequently booted normally with the retained, narrower controls. See [lessons](lessons.md) for the failure boundaries and [rooting](rooting.md) for the destructive historical sequence.

## What the hardware results do not establish

- The generalized Python configuration/scheduler builders have unit tests with simulated responses. They were extracted after the hardware work and have not been reapplied as a new batch to either TV.
- The public neutral sample animation is generated separately; it has not been installed on those TVs. The hardware tests used custom artwork whose branding and files remain private.
- Successful launcher/app launches are not a comprehensive media-playback, HDMI picture/sound, reliability or performance benchmark.
- Persisted software microphone/ACR controls are not physical microphone removal or a complete audit of proprietary network traffic.
- A successful dry run and daemon restart are distinct from observing an actual scheduled clock-triggered sleep event.

Verify your own device identity, firmware, dependencies and recovery path before adapting the tools. Keep new hardware results scoped to the actual checks performed rather than marking an entire model family universally supported.
