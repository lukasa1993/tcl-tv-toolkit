#!/usr/bin/env python3
"""Authenticated HTTP client for the TV UART bridge; secrets stay in private/."""
import argparse
import json
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import urllib.parse
import uuid
import webbrowser

ROOT = Path(__file__).resolve().parent
LOCAL_HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(host, path, body=None):
    token = (ROOT / "private/access-token").read_text().strip()
    if path == "/tx" and body is not None:
        if len(body) > 4096:
            raise ValueError("Maximum UART write is 4096 bytes")
        body = body.hex().encode("ascii")
    req = urllib.request.Request(
        f"http://{host}:8080{path}", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
    )
    return LOCAL_HTTP.open(req, timeout=15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="tcl-uart-bridge.local")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("open", help="Open authenticated control page in the default browser")
    update = sub.add_parser("update", help="Upload firmware.bin over authenticated Wi-Fi OTA")
    update.add_argument("firmware", type=Path)
    sub.add_parser("automation", help="Show automation status without reading TV UART")
    sub.add_parser("disarm", help="Stop transmissions and clear all boot ARM flags")
    rx = sub.add_parser("read")
    rx.add_argument("--follow", action="store_true")
    rx.add_argument("--save", type=Path)
    send = sub.add_parser("send")
    send.add_argument("text", nargs="?")
    send.add_argument("--stdin", action="store_true")
    send.add_argument("--enter", action="store_true", help="Append carriage return")
    for name in ["enter", "arm-next-boot"]:
        cmd = sub.add_parser(name)
        cmd.add_argument("seconds", type=int, choices=range(31))
    args = parser.parse_args()
    if args.command == "open":
        token = (ROOT / "private/access-token").read_text().strip()
        url = f"http://{args.host}:8080/#key={urllib.parse.quote(token, safe='')}"
        if not webbrowser.open(url):
            raise RuntimeError("Could not open browser; open the bridge URL and enter private/access-token")
        print("Opened control page; access key is not printed.")
    elif args.command == "update":
        token = (ROOT / "private/access-token").read_text().strip()
        boundary = "esp32-" + uuid.uuid4().hex
        firmware = args.firmware.read_bytes()
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="firmware"; filename="firmware.bin"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n').encode() + firmware
        body += f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(f"http://{args.host}:8080/update", data=body,
            headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary}"})
        with LOCAL_HTTP.open(req, timeout=120) as response:
            print(response.read().decode())
    elif args.command == "automation":
        with request(args.host, "/automation") as response:
            print(json.dumps(json.load(response), indent=2))
    elif args.command == "disarm":
        with request(args.host, "/automation/disarm", b"stop=1") as response:
            print(response.read().decode())
    elif args.command == "status":
        with request(args.host, "/status") as response:
            print(json.dumps(json.load(response), indent=2))
    elif args.command == "send":
        if args.stdin:
            payload = sys.stdin.buffer.read()
        elif args.text is not None:
            payload = args.text.encode()
        else:
            parser.error("send needs text or --stdin")
        if args.enter:
            payload += b"\r"
        with request(args.host, "/tx", payload) as response:
            print(response.read().decode())
    elif args.command in ["enter", "arm-next-boot"]:
        with request(args.host, "/" + args.command, str(args.seconds).encode()) as response:
            print(response.read().decode())
    else:
        cursor = 0
        output = args.save.open("ab") if args.save else None
        try:
            while True:
                try:
                    with request(args.host, f"/rx?since={cursor}") as response:
                        data = response.read()
                        lost = int(response.headers["X-UART-Lost"])
                        cursor = int(response.headers["X-UART-End"])
                except urllib.error.HTTPError as error:
                    if error.code == 409:
                        print("Bridge restarted or capture wrapped; resuming retained log.", file=sys.stderr)
                        cursor = 0
                        if not args.follow:
                            raise
                        continue
                    raise
                except (OSError, urllib.error.URLError) as error:
                    if not args.follow:
                        raise
                    print(f"Waiting for bridge: {error}", file=sys.stderr)
                    time.sleep(2)
                    continue
                if lost:
                    print(f"Capture buffer dropped {lost} earlier bytes.", file=sys.stderr)
                if data:
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    if output:
                        output.write(data)
                        output.flush()
                if not args.follow:
                    break
                time.sleep(0.2)
        finally:
            if output:
                output.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
