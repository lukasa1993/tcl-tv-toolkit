# Obtain, match and patch a boot image

This is the detailed **T653T01 V643** reference. Other firmware needs its own evidence. A package filename, matching screen size or model name alone does not prove compatibility. Do not downgrade a TV or install the whole firmware package merely to follow this guide.

## 1. Match the actual target

Save discovery before a reset. Confirm `V8-T653T01-LF1V643`, Android 14, `merak` / `mt5896`, bootloader version, active slot, kernel and boot security properties on the actual TV. Inspect `/dev/block/by-name/` when accessible. Establish that the relevant partition is `boot_a` with an existing ramdisk; do not infer `init_boot`, `vendor_boot` or `_a` from Android version alone. If the observed layout differs, stop this reference branch and investigate that build.

The saved stock image was Android boot-header **v4**, **56,623,104 bytes**. Its ramdisk's build family was `TCL/G08_4K_GB/G08:14/UTT2.250416.001/AU02:user/release-keys`, and its boot build timestamp was `1775962839`. The downloaded OTA metadata instead identifies the **US** regional build family. This regional difference is real; do not erase it from the evidence or require every image property to equal the Android system fingerprint. The original work checked the actual target's build information and AVB-chain digest too. Any unexplained mismatch needs investigation before flashing.

Recorded 55C6K pre-unlock `ro.boot.vbmeta.digest` was `2fb2735d099d2f3a5bb1b995b4bb4fba502acf5861471746c6037fe31fecbd7e`. The retained verification recorded `18cc2ad0030e12398c8e3372f5c011426f263ab2b0f4f120a05b2dc7ef0c93b2` for the AVB chain with hashtree disabled, matching the TV in that state. These are corroborating firmware/security-state evidence, not interchangeable stock/patched boot hashes. Preserve the target's actual digest and flags; investigate a mismatch rather than changing the TV's verification state just to obtain an expected value. The full historical chain-reconstruction script was not preserved in this public toolkit.

## 2. Obtain the original package and retain an untouched image

The historical community mirror is [V8-T653T01-LF1V643.zip on Yandex Disk](https://disk.yandex.ru/d/erpa-VtUnU-AaA). On 2026-10-06 the public API and ZIP central directory identified a **2,360,177,508-byte** archive containing a direct root-level `boot.img` of **56,623,104 bytes**. This check read archive metadata, not a new full-image download. The stock-image hash below comes from the retained original used in the hardware work.

Yandex's download button supplies the archive. An agent can use the public endpoints `https://cloud-api.yandex.net/v1/disk/public/resources` and `/resources/download` with the mirror URL in the URL-encoded `public_key` query parameter. The latter returns a temporary `href`; keep it local. Download into `.local/firmware/`. No account credentials are needed for a public link. If the mirror disappears, obtain a matching package from another source and independently verify it; do not silently substitute a different build.

Extract only the needed entry, checking the recorded stock SHA256:

```sh
python3 tools/firmware.py extract .local/firmware/V8-T653T01-LF1V643.zip \
  --sha256 a5b49fe6c0ceee39e06f8ace64ed73cfa39ed9625d593a4903e9f25cf1c68c2e
python3 tools/firmware.py inspect .local/firmware/stock-boot.img
```

The extractor rejects duplicate `boot.img` entries, bad CRC/hash, unsupported headers and overwrite of an existing original. It prints the OTA metadata. Recorded fields: `ota-type=BLOCK`, `pre-device=G08`, `post-software-version-id=V8-T653T01-LF1V643`, SDK 34, security patch `2025-12-05`, post timestamp `1775964115`, post build `TCL/G08_4K_US/G08:14/UTT2.250416.001/AU02:user/release-keys`.

A matching digest establishes equality with this recorded artifact, not the trustworthiness of every mirror or compatibility with every TV. Other OTA formats may contain `payload.bin` or only incremental changes. The author's [payload_dumper](https://github.com/vm03/payload_dumper) is a separate extraction option; an incremental package may need an exact base image. The local extractor deliberately refuses to guess that workflow.

If already rooted, an original partition backup is another source. Resolve the real block device and capacity first. Use binary-safe `adb exec-out` redirection to a new ignored file, validate its length, `ANDROID!` header and hash, and compare on-device and pulled hashes. A shell error saved as `.img` is not a backup. Never overwrite the only known original with an unverified capture or a partition already patched by Magisk.

## 3. Obtain the recorded Magisk release

Use the author's [Magisk 30.7 release](https://github.com/topjohnwu/Magisk/releases/tag/v30.7), not an APK aggregator. Download locally:

```sh
mkdir -p .local/firmware
curl --fail --location --output .local/firmware/Magisk-v30.7.apk \
  https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk
python3 -c 'import hashlib,pathlib; p=pathlib.Path(".local/firmware/Magisk-v30.7.apk"); print(hashlib.sha256(p.read_bytes()).hexdigest())'
```

Expected APK SHA256: `e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5`. Stop on mismatch. New releases need new validation; the recorded choice does not mean 30.7 stays newest.

## 4. Patch on the actual TV

The [author's installation guide](https://topjohnwu.github.io/Magisk/install.html) requires patching on the target device. A patched image from another owner or another model is not a portable artifact. In the following commands, replace `YOUR_ADB_TARGET` everywhere, and include the same `-P` server-port option used in local config when needed.

```sh
adb -s YOUR_ADB_TARGET install -r .local/firmware/Magisk-v30.7.apk
adb -s YOUR_ADB_TARGET push .local/firmware/stock-boot.img /sdcard/Download/stock-boot.img
```

Open Magisk on that TV, record its ramdisk indication, choose **Install → Select and Patch a File**, and select `Download/stock-boot.img`. Record the output filename from the app log, then pull that exact file:

```sh
adb -s YOUR_ADB_TARGET pull /sdcard/Download/YOUR_EXACT_MAGISK_PATCHED_FILENAME.img .local/firmware/patched-boot.img
python3 tools/firmware.py compare .local/firmware/stock-boot.img .local/firmware/patched-boot.img
```

The reference patch retained `KEEPVERITY=true` and `KEEPFORCEENCRYPT=true`; verify these in the patched ramdisk. Do not assume the UI defaults have preserved them. Magisk's [30.7 patch script](https://github.com/topjohnwu/Magisk/blob/v30.7/scripts/boot_patch.sh) accepts explicit flag environment variables. Its [utility script](https://github.com/topjohnwu/Magisk/blob/v30.7/scripts/util_functions.sh) also derives flags from the device environment. Bootloader verity state and ramdisk patch flags are different things.

For inspection, prepare tools from the verified APK using the **TV's** `ro.product.cpu.abi`:

```sh
adb -s YOUR_ADB_TARGET shell getprop ro.product.cpu.abi
python3 tools/magisk_bundle.py .local/firmware/Magisk-v30.7.apk --abi arm64-v8a
adb -s YOUR_ADB_TARGET push .local/magisk-patch /data/local/tmp/tv-magisk-patch
adb -s YOUR_ADB_TARGET push .local/firmware/patched-boot.img /data/local/tmp/tv-magisk-patch/patched-boot.img
adb -s YOUR_ADB_TARGET shell
```

In the TV shell, in a fresh inspection directory:

```sh
cd /data/local/tmp/tv-magisk-patch
chmod 755 busybox magisk magiskboot magiskinit init-ld
mkdir verify
cd verify
../magiskboot unpack ../patched-boot.img
../magiskboot cpio ramdisk.cpio test
echo $?
# The preceding test must return 1 (Magisk), not 0 (stock) or 2 (unsupported).
../magiskboot cpio ramdisk.cpio 'extract .backup/.magisk patch-flags.txt'
cat patch-flags.txt
```

Check both flags, the recorded stock backup SHA1 and the presence of Magisk ramdisk files. If the UI produced different flags, stop before flashing. An agent may use the same-device script below to explicitly retain the reference flags, after investigating the target's encryption/verity layout. This is an **alternative patch step**, not an additional flash:

```sh
# In a fresh TV patch workspace containing the verified bundle, not its verify subdirectory:
cd /data/local/tmp/tv-magisk-patch
ASH_STANDALONE=1 BOOTMODE=true KEEPVERITY=true KEEPFORCEENCRYPT=true \
  PATCHVBMETAFLAG=false RECOVERYMODE=false LEGACYSAR=false \
  ./busybox sh ./boot_patch.sh /sdcard/Download/stock-boot.img
```

The script generates `new-boot.img` in that directory. Pull it into a **new** ignored filename, repeat local kernel/size comparison and on-TV ramdisk inspection, and retain its patch log. This bundle and alternative recipe were checked against the release contents/source; the extracted portable recipe has not been rerun on either TV. Use the app workflow first. Do not weaken an unexplained verification check just to proceed.

The local comparator checks header version, unchanged raw kernel, changed ramdisk and size no larger than the stock image. It does not validate AVB chains, Magisk flags or target compatibility. Historical patched SHA256 was `9653a7e1bc17713435c5b59e67ace852a188965a855efe4c9cdebed9f7478808`; record your own result rather than requiring a fresh device patch to equal it.

## 5. Prepare the flash drive and stop at the flashing gate

Use a compatible FAT32 drive. If formatting is required, identify the physical drive and obtain explicit erase authorization; no toolkit command formats disks. Put stock and verified patched images at the drive root with simple ASCII filenames, plus a hash record. Read back both from the mounted drive and verify hashes, then eject cleanly. The filename in the UART command must exactly match the patched filename. Use the TV's verified active boot partition; the historical target was `boot_a`.

Confirm a recovery route, backups, firmware/slot/ramdisk match, drive contents and current owner authorization before proceeding to [the runbook's unlock stage](runbook.md#5-unlock-and-flash-only-if-required). This repository does not establish a universal offline TCL recovery-key combination or vendor rescue image for other builds.
