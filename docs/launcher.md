# Projectivy and retained apps

Use [Projectivy's author project](https://github.com/spocky/miproja1) or the TV's app store for installation. The reference used Projectivy 4.71; obtain your own app and verify its provenance. This repo does not redistribute third-party APKs, account databases or imported user backups.

## Minimal layout

In Projectivy, create a favorites row containing only your retained apps, in your preferred order. Hide other categories, unused inputs and promotional rows. Leave Settings reachable. Keep a connected HDMI input if you need one; do not copy another device's input selection or subscription/library content.

If Plex shows its free catalog, adjust Plex's pinned sources and channel rows to retain your own server/library content. Account login and library selection remain local user configuration. Projectivy favorites are independent of Plex authentication.

Configure Projectivy as default Home using its own settings. Before disabling the stock home packages, prove that Home and Settings work and save the original preferred activity and enabled states. Reference stock packages were `com.google.android.apps.tv.launcherx` and `com.google.android.tungsten.setupwraith`; they are intentionally absent from the automated debloat profile to avoid leaving a TV without a working home screen.

Projectivy's settings export/import is version-sensitive and includes user configuration. Keep exports under `.local/`. Configure through the UI instead of modifying its internal database or copying favorite IDs from a different installation.

## Agent configuration: commands versus UI

Before any Home/accessibility changes, capture the current preferred Home, enabled states of both stock packages, `enabled_accessibility_services`, `accessibility_enabled` and each package's vendor `AUTO_START` mode in `.local/`. Install Projectivy first and inspect its registered Home activity/accessibility service on this build. These commands illustrate the reference packages; run changes only after confirming them and retaining rollback.

Read-only baseline/verification:

```sh
adb -s YOUR_ADB_TARGET shell cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.HOME
adb -s YOUR_ADB_TARGET shell dumpsys package com.spocky.projengmenu
adb -s YOUR_ADB_TARGET shell dumpsys package com.google.android.apps.tv.launcherx
adb -s YOUR_ADB_TARGET shell dumpsys package com.google.android.tungsten.setupwraith
adb -s YOUR_ADB_TARGET shell settings get secure enabled_accessibility_services
adb -s YOUR_ADB_TARGET shell settings get secure accessibility_enabled
adb -s YOUR_ADB_TARGET shell dumpsys accessibility
adb -s YOUR_ADB_TARGET shell cmd appops get com.spocky.projengmenu AUTO_START
```

Use Projectivy's own Settings and Android's accessibility UI to enable its service. On the reference it was `com.spocky.projengmenu/com.spocky.projengmenu.services.ProjectivyAccessibilityService`. If changing `enabled_accessibility_services` programmatically, preserve existing valid services, append only once with a colon separator and do not insert a leading colon or replace the whole list. Verify actual binding via `dumpsys accessibility`. A saved setting isn't proof of a live service.

In an interactive verified root shell, the reference Home grant/selection commands were:

```sh
pm grant com.spocky.projengmenu android.permission.READ_TV_LISTINGS
cmd package set-home-activity --user 0 com.spocky.projengmenu
```

If an operation is unsupported or the permission is not declared, investigate the installed version rather than adding guessed permissions. Verify Home navigation and Settings before optionally disabling stock Home/setup in that same root shell:

```sh
pm disable-user --user 0 com.google.android.apps.tv.launcherx
pm disable-user --user 0 com.google.android.tungsten.setupwraith
cmd package set-home-activity --user 0 com.spocky.projengmenu
```

Restore the **saved original enabled states and preferred Home** to undo. The package `pm enable` command alone cannot restore a previous preferred activity or a nondefault enabled state.

Favorites, channel ordering, connected-input selection, app account/library choices, appearance and optional analytics/crash/performance switches are configured through the exposed UI and exported privately. An agent with UI control can do those steps; otherwise provide the owner a concise UI checklist while continuing independent inspection. This repo supplies no portable internal Projectivy database editor or another owner's account/channel backup.

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

After recording baseline modes, the reference command was `cmd appops set com.spocky.projengmenu AUTO_START allow`, followed by the same operation for the **actual chosen startup package** and, where needed, `com.plexapp.android` for its media service. Perform this in a verified root shell, rebind accessibility through the UI, and verify modes/binding afterward. Restore each recorded mode to undo; unsupported vendor operations must be investigated, not silently treated as successful. The `power_*` values above describe observed preferences; choose them in Projectivy's UI rather than pasting them into Android `settings` or editing a private preferences file blindly.

## Optional telemetry and verification

The reference turned off Projectivy's optional analytics, crash reporting and Firebase performance switch. Use the app's exposed switches where possible; recheck after updates. This does not prove the app or every SDK makes zero network requests.

Verify your chosen app opens after boot and wake, other apps open only when selected, Home returns to the intended launcher, Settings remains accessible, and actual playback works. The configuration tools do not launch apps or test playback automatically.
