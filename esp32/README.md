# ESP32 Wi-Fi UART bridge

ESP32-WROOM-32 / `esp32dev`, UART2 at 115200 8N1: GPIO25 RX, GPIO26 TX, GND. See the [device-specific service-port wiring notes](../docs/rooting.md) before connecting a TV. USB supplies ESP power or computer firmware flashing, not a TV USB data bridge.

## Build and commission

Install PlatformIO in the runbook's local environment and use the pinned [pioarduino platform release](https://github.com/pioarduino/platform-espressif32/releases/tag/55.03.38). `setup_bridge.py` prompts for SSID/password and creates matching private configuration/token files with restrictive permissions. It refuses to overwrite them, so an existing bridge's credentials aren't silently rotated. Both files are ignored. Do not paste credentials into issues or commit them. Manual configuration from `config.example.h` remains possible.

```sh
python3 esp32/setup_bridge.py
pio run -d esp32
# First installation needs a USB cable to the computer:
pio device list
pio run -d esp32 -t upload --upload-port YOUR_CONFIRMED_ESP_USB_PORT
python3 esp32/bridge.py --host tcl-uart-bridge.local status
python3 esp32/bridge.py --host tcl-uart-bridge.local open
```

If mDNS fails, use your own ESP address. The bridge listens on port 8080. Authentication uses plain local HTTP, so use a trusted isolated LAN and do not expose it to the internet. Wi-Fi credentials and token are embedded in compiled firmware; keep `.pio/` and firmware BINs private.

Before attaching the TV, verify internal UART loopback through the authenticated `/commissioning-loopback` endpoint (`1` enables; `0` disables and permanently closes commissioning):

```sh
python3 esp32/bridge.py disarm
python3 esp32/bridge.py loopback on
python3 esp32/bridge.py send LOOPBACK_TEST --enter
python3 esp32/bridge.py read
# Confirm the marker appears in received data, then close internal loopback:
python3 esp32/bridge.py loopback close
python3 esp32/bridge.py update esp32/.pio/build/esp32dev/firmware.bin
# Wait for network return; verify status and automation both report disarmed.
python3 esp32/bridge.py status
python3 esp32/bridge.py automation
```

Use `--host YOUR_ESP_ADDRESS` before each subcommand if mDNS fails. OTA is tested while the TV is detached; it updates the application and does not intentionally erase the stored token/closed commissioning state. A reused ESP may return 409 because commissioning was already closed; don't erase its settings just to repeat loopback. Preserve existing credentials and diagnose the physical UART separately.

Then wire the verified service port. Receive capture is passive and bounded; `bridge.py read --follow` reads it, with dropped-buffer/restart handling. Unreadable replies require hardware/timing diagnosis, not assuming command success. Internal loopback does not test the TV or its connector.

## Control page

`bridge.py open` opens the page with the key in the URL fragment and removes that fragment after loading. It does not print the token. Alternatively open `http://YOUR_ESP_ADDRESS:8080` and enter your key.

- **Dry run:** event timeline, no UART bytes.
- **Start now:** starts the configured timeline immediately.
- **ARM next ESP startup:** one-shot run, with the stored ARM flag consumed before UART transmission. Restarting only an independently powered TV does not restart the ESP.
- **DISARM / STOP:** cancels future bytes and clears persistent ARM flags. It cannot reverse commands already sent.
- **OTA:** application `firmware.bin` upload clears ARM, stops automation, updates and restarts disarmed. Do not use a merged/factory binary.

Timing includes start delay, Enter burst, interval, quiet interval, commands and wait after each. Profiles allow up to 12 printable ASCII commands of 256 characters each. Timing is an estimate; the bridge does not interpret U-Boot or acknowledge TV execution. The initial diagnostic requests `version`. Loading unlock commands explicitly warns about factory reset. The incomplete reference flash JSON contains placeholders and must be reviewed/adapted locally; it isn't a default saved sequence.

```sh
python3 esp32/bridge.py run --profile examples/bridge-profile.json
python3 esp32/bridge.py automation
python3 esp32/bridge.py disarm
python3 esp32/bridge.py update esp32/.pio/build/esp32dev/firmware.bin
```

`update` is an actual mutation of the ESP. Build alone does not flash or contact any TV. Keep the ESP disarmed after finishing bootloader work.

`profile FILE` saves validated timings/commands without transmitting. `run --profile FILE` defaults to dry mode. Live `--mode now` or one-shot `--mode arm` requires `--accept-reset-risk`; only use that flag within the current owner's authorization after the runbook gates. Changing a profile while armed/running returns 409: disarm first. The web page exposes the same modes. Timeline times are milliseconds; a stall does not replay missed Enter intervals, and completion means the ESP sequence ended, not that the TV completed the commands.
