# Daily on-TV sleep schedule

The main schedule is a private Magisk BusyBox cron process **on the TV**, started by a script under `/data/adb/service.d/`. It does not depend on a computer, ESP, Wi-Fi, ADB or a cloud account once installed. Android must be running and the TV's clock must be correct.

Set a local time and fixed UTC offset in ignored `config.local.json`, then generate scripts:

```json
"sleep": {"local_time": "01:00", "utc_offset": "+04:00"}
```

```sh
python3 tools/sleep.py
```

For that example, the daily crontab is `0 21 * * *`: 21:00 UTC equals 01:00 UTC+4. The daemon exports `TZ=UTC`; Android's existing timezone stays unchanged. Fixed offsets do not track daylight saving. If your timezone changes seasonally, regenerate the time intentionally.

## Review and install

The generator contacts no device. Inspect `.local/sleep/` first. Replace the target below with the same verified ADB target from your local config; include `-P` if using a dedicated ADB server.

```sh
adb -s YOUR_ADB_TARGET push .local/sleep /data/local/tmp/tv-sleep-install
adb -s YOUR_ADB_TARGET shell
/debug_ramdisk/su
sh /data/local/tmp/tv-sleep-install/install.sh
```

Your `su` path may differ. The installer checks root and serial, refuses to overwrite an existing installation, protects its private directories and starts a dedicated daemon. Its final `--test` reports state without sending sleep.

| On-TV location | Purpose |
| --- | --- |
| `/data/adb/tv-nightly-sleep/cron/root` | Private root crontab |
| `/data/adb/tv-nightly-sleep/sleep-tv.sh` | Identity/time/boot/wake checks and sleep request |
| `/data/adb/tv-nightly-sleep/start-scheduler.sh` | Duplicate-checked daemon startup |
| `/data/adb/service.d/90-tv-nightly-sleep.sh` | Startup hook |
| `/data/adb/tv-nightly-sleep/crond.pid` | Private daemon PID |
| `/data/adb/tv-nightly-sleep/actions.log` | Actual sleep requests |
| `/data/adb/tv-nightly-sleep/cron.log` | Cron daemon log |

The action sends **KEYCODE_SLEEP 223** only when Android reports Awake. It does not send a wake or power-toggle key, open an app, or reboot. An already sleeping TV is left alone. It is one daily event, not a lockout: someone can turn the TV on again afterward.

## Verify and cancel

Check the private crontab, PID command line, `TZ=UTC` daemon environment and `--test` output. After a deliberate reboot, repeat those checks. Observe an actual scheduled event and inspect `actions.log`; a successful dry run or sleep-key test does not establish that the clock-triggered event already happened.

To cancel, as root:

```sh
sh /data/adb/tv-nightly-sleep/disable-scheduler.sh
```

It creates a disabled marker, stops only the verified private cron PID and removes the startup hook. Files/logs remain for inspection. The disabled marker also makes the action itself a no-op.

An optional external scheduler can provide a backup check. Keep its connection details outside this repo, restrict it to a narrow scheduled window, verify the target identity, and send sleep only if awake. It should skip unreachable devices and never try to wake them. If you use both local and external timers, disable both to fully cancel. This repository contains no active external automation or personal host configuration.
