# ESP32 Wi-Fi UART bridge

ESP32-WROOM-32 / `esp32dev`, UART2 at 115200 8N1: GPIO25 RX, GPIO26 TX, GND. See the [device-specific service-port wiring notes](../docs/rooting.md) before connecting a TV. USB supplies ESP power or computer firmware flashing, not a TV USB data bridge.

## Build and commission

Install PlatformIO and use the pinned [pioarduino platform release](https://github.com/pioarduino/platform-espressif32/releases/tag/55.03.38). Copy `config.example.h` into `private/config.h`, fill Wi-Fi credentials and a random bearer token, and put the same token in `private/access-token`. Both files are ignored. For example, generate a token locally with `python3 -c 'import secrets; print(secrets.token_hex(32))'`; do not paste it into issues or commit it.

```sh
cd esp32
pio run
# First installation needs a USB cable to the computer:
pio run -t upload
python3 bridge.py --host tcl-uart-bridge.local status
python3 bridge.py --host tcl-uart-bridge.local open
```

If mDNS fails, use your own ESP address. The bridge listens on port 8080. Authentication uses plain local HTTP, so use a trusted isolated LAN and do not expose it to the internet. Wi-Fi credentials and token are embedded in compiled firmware; keep `.pio/` and firmware BINs private.

Before attaching the TV, verify internal UART loopback through the authenticated `/commissioning-loopback` endpoint (`1` enables; `0` disables and permanently closes commissioning). Then wire the verified service port. Receive capture is passive and bounded; `bridge.py read --follow` reads it, with dropped-buffer/restart handling. Unreadable replies require hardware/timing diagnosis, not assuming command success.

## Control page

`bridge.py open` opens the page with the key in the URL fragment and removes that fragment after loading. It does not print the token. Alternatively open `http://YOUR_ESP_ADDRESS:8080` and enter your key.

- **Dry run:** event timeline, no UART bytes.
- **Start now:** starts the configured timeline immediately.
- **ARM next ESP startup:** one-shot run, with the stored ARM flag consumed before UART transmission. Restarting only an independently powered TV does not restart the ESP.
- **DISARM / STOP:** cancels future bytes and clears persistent ARM flags. It cannot reverse commands already sent.
- **OTA:** application `firmware.bin` upload clears ARM, stops automation, updates and restarts disarmed. Do not use a merged/factory binary.

Timing includes start delay, Enter burst, interval, quiet interval, commands and wait after each. Profiles allow up to 12 printable ASCII commands of 256 characters each. Timing is an estimate; the bridge does not interpret U-Boot or acknowledge TV execution. The initial diagnostic requests `version`. Loading unlock commands explicitly warns about factory reset; there is no preset image flashing sequence.

```sh
python3 bridge.py disarm
python3 bridge.py automation
python3 bridge.py update .pio/build/esp32dev/firmware.bin
```

`update` is an actual mutation of the ESP. Build alone does not flash or contact any TV. Keep the ESP disarmed after finishing bootloader work.
