#!/usr/bin/env python3
"""Generate device-specific sleep scripts locally; never connect to a TV."""
import argparse
import json
from pathlib import Path
import re
import shlex

ROOT = Path(__file__).resolve().parents[1]


def utc_time(local_time, offset):
    match = re.fullmatch(r"(\d{2}):(\d{2})", local_time)
    zone = re.fullmatch(r"([+-])(\d{2}):(\d{2})", offset)
    if not match or not zone:
        raise ValueError("Use HH:MM and a signed fixed UTC offset such as +04:00")
    hour, minute = map(int, match.groups())
    zh, zm = map(int, zone.groups()[1:])
    if hour > 23 or minute > 59 or zh > 14 or zm > 59 or (zh == 14 and zm):
        raise ValueError("Invalid time or UTC offset")
    delta = (zh * 60 + zm) * (1 if zone[1] == "+" else -1)
    return divmod((hour * 60 + minute - delta) % 1440, 60)


def generate(config):
    serial = config["expected_serial"]
    if not re.fullmatch(r"[A-Za-z0-9._-]+", serial) or "REPLACE" in serial:
        raise ValueError("Set a concrete TV serial in local config")
    hour, minute = utc_time(config["sleep"]["local_time"], config["sleep"]["utc_offset"])
    time = f"{hour:02}:{minute:02}"
    prelude = ('#!/system/bin/sh\nset -eu\nBASE=/data/adb/tv-nightly-sleep\n'
               'BB=/data/adb/magisk/busybox\n'
               f'[ "$(getprop ro.boot.serialno)" = {shlex.quote(serial)} ]\n'
               '[ "$(id -u)" = 0 ]\n')
    sleep = prelude + f'''[ ! -e "$BASE/disabled" ] || exit 0
if [ "${{1:-}}" != --test ]; then
  [ "$(TZ=UTC "$BB" date +%H:%M)" = {time} ] || exit 0
fi
[ "$(getprop sys.boot_completed)" = 1 ] || exit 0
STATE=$(dumpsys power | "$BB" grep 'mWakefulness=' | "$BB" head -n 1)
if [ "${{1:-}}" = --test ]; then
  echo "UTC schedule={time}; $STATE; sleep key=223; no command sent"
  exit 0
fi
case "$STATE" in
  *mWakefulness=Awake*)
    TZ=UTC "$BB" date '+%Y-%m-%dT%H:%M:%SZ sleeping TV' >> "$BASE/actions.log"
    /system/bin/input keyevent 223
    ;;
esac
'''
    verified_pid = '''if [ -f "$BASE/crond.pid" ]; then
  PID=$(cat "$BASE/crond.pid")
  case "$PID" in ''|*[!0-9]*) exit 1;; esac
  if kill -0 "$PID" 2>/dev/null && "$BB" tr '\\000' ' ' < "/proc/$PID/cmdline" | "$BB" grep -Fq "$BASE/cron"; then
'''
    start = prelude + '[ ! -e "$BASE/disabled" ] || exit 0\n' + verified_pid + '''    exit 0
  fi
fi
export TZ=UTC
"$BB" nohup "$BB" crond -f -c "$BASE/cron" -l 8 -L "$BASE/cron.log" </dev/null >/dev/null 2>&1 &
echo "$!" > "$BASE/crond.pid"
'''
    disable = prelude + 'touch "$BASE/disabled"\n' + verified_pid + '''    kill "$PID"
  fi
fi
rm -f /data/adb/service.d/90-tv-nightly-sleep.sh
echo 'TV sleep schedule disabled.'
'''
    install = prelude + '''[ -x "$BB" ]
[ ! -e "$BASE" ] || { echo 'Existing installation; disable and review it first' >&2; exit 1; }
SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$BASE/cron" /data/adb/service.d
cp "$SOURCE/sleep-tv.sh" "$SOURCE/start-scheduler.sh" "$SOURCE/disable-scheduler.sh" "$BASE/"
cp "$SOURCE/root" "$BASE/cron/root"
chown -R 0:0 "$BASE"
chmod 700 "$BASE" "$BASE/cron" "$BASE/"*.sh
chmod 600 "$BASE/cron/root"
echo '#!/system/bin/sh' > /data/adb/service.d/90-tv-nightly-sleep.sh
echo 'exec /system/bin/sh /data/adb/tv-nightly-sleep/start-scheduler.sh' >> /data/adb/service.d/90-tv-nightly-sleep.sh
chown 0:0 /data/adb/service.d/90-tv-nightly-sleep.sh
chmod 700 /data/adb/service.d/90-tv-nightly-sleep.sh
/system/bin/sh "$BASE/start-scheduler.sh"
/system/bin/sh "$BASE/sleep-tv.sh" --test
'''
    return {"sleep-tv.sh": sleep, "start-scheduler.sh": start, "disable-scheduler.sh": disable,
            "install.sh": install, "root": f"{minute} {hour} * * * /system/bin/sh /data/adb/tv-nightly-sleep/sleep-tv.sh\n"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.local.json")
    args = parser.parse_args()
    files = generate(json.loads(args.config.read_text()))
    output = ROOT / ".local" / "sleep"
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name, content in files.items():
        target = output / name
        target.write_text(content)
        target.chmod(0o600)
    print("Generated .local/sleep/; no device was contacted. Review before installation.")


if __name__ == "__main__":
    main()
