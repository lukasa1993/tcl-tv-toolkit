# Projectivy and retained apps

Use [Projectivy's author project](https://github.com/spocky/miproja1) or the TV's app store for installation. The reference used Projectivy 4.71; obtain your own app and verify its provenance. This repo does not redistribute third-party APKs, account databases or imported user backups.

## Minimal layout

In Projectivy, create a favorites row containing only your retained apps, in your preferred order. Hide other categories, unused inputs and promotional rows. Leave Settings reachable. Keep a connected HDMI input if you need one; do not copy another device's input selection or subscription/library content.

If Plex shows its free catalog, adjust Plex's pinned sources and channel rows to retain your own server/library content. Account login and library selection remain local user configuration. Projectivy favorites are independent of Plex authentication.

Configure Projectivy as default Home using its own settings. Before disabling the stock home packages, prove that Home and Settings work and save the original preferred activity and enabled states. Reference stock packages were `com.google.android.apps.tv.launcherx` and `com.google.android.tungsten.setupwraith`; they are intentionally absent from the automated debloat profile to avoid leaving a TV without a working home screen.

Projectivy's settings export/import is version-sensitive and includes user configuration. Keep exports under `.local/`. Configure through the UI instead of modifying its internal database or copying favorite IDs from a different installation.

## Start one app on boot and wake

Choose exactly one automatic startup source in Projectivy. The observed preferences were:

```text
power_autostart_source = YOUR_APP_PACKAGE
power_autostart_delay = 5
power_autostart_leaving_standby = true
```

Projectivy's accessibility service must be enabled and bound for wake behavior. On the reference firmware, TCL's vendor `AUTO_START` AppOp blocked that service. Allowing it for Projectivy and the selected app, then rebinding the service, restored boot/wake startup.

Plex also needed `AUTO_START` allowed to bind its media audio service. A service permission does not select an app as the automatic foreground launch target. Keep Projectivy's source pointed at your chosen app; opening Plex manually during testing can otherwise look like unexpected auto-start.

Vendor operations may differ by firmware. Save previous modes before changes. Test reboot and remote wake separately. UI automation dumps can temporarily unbind accessibility services; inspect the live binding before treating a transient toast as a permanent failure.

## Optional telemetry and verification

The reference turned off Projectivy's optional analytics, crash reporting and Firebase performance switch. Use the app's exposed switches where possible; recheck after updates. This does not prove the app or every SDK makes zero network requests.

Verify your chosen app opens after boot and wake, other apps open only when selected, Home returns to the intended launcher, Settings remains accessible, and actual playback works. The configuration tools do not launch apps or test playback automatically.
