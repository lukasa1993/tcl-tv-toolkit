# Rooting and recovery

## Inspect before changing anything

Record the model label, complete software version, Android version, security patch, board, build fingerprint, active slot, and boot security state. Developer options and ADB authorization allow inspection; they do not themselves provide root. Collect read-only properties with `adb shell getprop` and keep the output in ignored local storage.

Rooting work succeeded on both **TCL 75P8K and TCL 55C6K**; see the [tested-device record](tested-devices.md). The detailed firmware reference for the sequence below was the 55C6K on V8-T653T01-LF1V643 / Android 14, reported board `merak`, hardware `mt5896`, active slot `_a`. Model labels can cover different firmware and hardware. Never use this list as a substitute for your own device inspection.

A normal TV USB-A socket is generally a host port for drives or power. The observed TV-to-computer USB test did not expose usable fastboot/ADB. An ESP connected only through its USB power socket does not create a TV console connection. Do not assume an undocumented USB socket is a device port.

## Service UART and ESP

The reference connection used the HDMI socket marked **Service** and a plain connector/breakout, plus the [ESP32 bridge](../esp32/README.md). It did not use an optical HDMI cable as a UART adapter.

| HDMI contact in observed service implementation | ESP32 signal |
| --- | --- |
| 14 | GPIO25, UART RX (TV output) |
| 2 | GPIO26, UART TX (TV input) |
| 11 | GND |

UART: **115200, 8N1**. Verify contact numbering from the mating face and continuity from each contact to each wire with everything unpowered. Cable colors and PCB solder-pad order are not universal. Check for shorts between the three wires. Verify the TV logic voltage against ESP32 input limits before connecting; this mapping is not guaranteed for every TCL service port. Power the ESP by USB, without connecting HDMI pin 18 to its power rail.

Commission the bridge without TV wiring first. Check network control, capture and loopback, then close commissioning. With independently powered ESP, ARM means **next ESP startup**, not next TV startup. Use Start now and boot the TV during the Enter burst, or restart both deliberately after one-shot ARM. DISARM stops future bytes; it cannot undo commands already sent.

Reliable readable UART was not established in the reference work. Transmission logs establish bytes sent by the ESP only. A black screen is not evidence of U-Boot, successful unlock, or completed flashing. The default diagnostic is `version`; the bridge can capture replies if your hardware path works.

## Prepare your own image

Follow [firmware preparation](firmware.md) for the recorded source/hash, exact extraction, on-target patch and ramdisk inspection. Preserve the stock boot image, partition layout, exact fingerprint, slot, byte size and SHA256 before patching. Use the matching stock boot image and verified [Magisk release](https://github.com/topjohnwu/Magisk/releases), and follow the [Magisk installation guide](https://topjohnwu.github.io/Magisk/install.html). Keep both stock and patched images on the prepared FAT32 drive. Do not redistribute firmware backups in this repo.

The reference used Magisk 30.7 on an exactly matched V643 boot image. Each image was 56,623,104 bytes; this number is an observation, not a universal size requirement. The payload targeted `boot_a` because `_a` was the verified active slot.

## Historical bootloader sequence

**Destructive, device-specific reference only. Unlocking reset setup and accounts. A wrong command or image may make the TV unbootable. Nothing flashes by default.** A rooted TV does not need this sequence repeated. The [runbook](runbook.md#5-unlock-and-flash-only-if-required) explains local adaptation of the deliberately incomplete reference profile, dry run, current authorization and explicit live execution.

The observed profile sent Enter every 100 ms for 60 seconds, waited two seconds, then transmitted:

| Command | Wait afterward |
| --- | --- |
| `env set devicestate unlock` | 2 s |
| `avb init mmc` | 2 s |
| `avb set-devicestate 0` | 2 s |
| `avb set-verity disable` | 2 s |
| `saveenv` | 5 s |
| `usb start` | 5 s |
| `usb_partial_upgrade_to_emmc YOUR_MATCHED_PATCHED_BOOT.img boot_a` | 60 s |
| `reset` | 2 s |

These waits are transmission timings, not confirmations of bootloader completion. This route came from [community TCL discussion](https://4pda.to/forum/index.php?showtopic=1080227&st=34540); access to the full discussion was limited. Local device evidence established compatibility for the reference unit. Use a readable console and device-specific recovery documentation where available.

The first attempt showed black. An Enter-only retry was followed by an unlocked message and setup wizard. After network setup, ADB authorization, installing the full verified Magisk manager, accepting its additional-setup reboot and granting root, rooted ADB confirmed `uid=0(root)`. Verification also showed unlocked/orange boot state and SELinux Enforcing. No SELinux-permissive command was required.

## Recovery boundaries

Back up configuration before unlocking and expect a setup reset. Have the original image and a firmware recovery route prepared before flashing. Android rollback scripts in this toolkit work only while rooted Android is functioning; they are not a guaranteed rescue mechanism for a bootloader or boot-partition failure.

Do not relock with a patched boot image installed. Do not blindly restore raw bootdata/vbmeta partitions. After a black screen, first inspect actual power/boot state and available logs rather than replaying destructive commands. Follow the [recovery decision branches](recovery.md). Once rooted ADB works, use it for configuration and leave the ESP disarmed.
