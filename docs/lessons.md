# Lessons and limits

- **Unlock can reset everything.** One early attempt reset a TV without adequately warning about setup/account loss. Document that consequence before transmission and preserve configuration first.
- **A black screen proves little.** Neither black nor a bridge transmission log establishes U-Boot or flash success. Later setup screens, root identity and boot-state properties supplied the actual proof.
- **Preserve shared core UIDs.** An overbroad privacy Magisk module and shared-UID recording restrictions were followed by a startup hang. The failed module was disabled and core audio settings restored. It is not included here. The exact causal contribution of each restriction was not isolated; avoid recreating that batch.
- **Use persisted, narrow controls.** User restrictions, per-operation application AppOps, specific ACR components and reversible optional-package disabling survived normal reboot in the reference configuration.
- **Service permission differs from foreground startup.** A media service may need vendor AUTO_START without the app being the configured automatic launch target. Verify both separately.
- **Build a portable launcher layout.** Favorites, HDMI selection, subscriptions and personal-library rows belong to local configuration. Do not copy another installation's account data or internal item IDs.
- **Measure performance before claiming gains.** Optional app cleanup was reversible. Kernel, swap, compositor and aggressive process-limit tweaks were not applied, and no benchmarked speedup was established.
- **Do not hide network failures with broad blocks.** An attempted network-validation workaround did not establish a fix for intermittent video transport issues. Blanket router/DNS rules were not carried into the reusable configuration.
- **Verify the real action.** ADB can time out after sleep/reboot even when the action occurred. Check screen/uptime/boot properties before repeating a command. Do not use a power-toggle key to diagnose transport loss.
- **Keep a recovery boundary.** Target-specific Android rollback scripts are useful only with functioning rooted Android. Neither they nor a stock image alone guarantee bootloader recovery.
- **Software controls have limits.** The microphone was software-muted and candidate collection services disabled; no physical mic removal or comprehensive proprietary traffic audit was performed.

The generalized tools introduce explicit config, baseline and dry-plan handling. Their unit tests simulate Android responses. They are not a claim that a newly generated batch has already run on real hardware.
