# Privacy controls and reversible cleanup

The candidate profile is an observed T653T01 V643 configuration. Edit it for your own firmware and retained functions before generating a plan. It contains optional package names, persisted settings and specific components rather than disabling all shared TV services.

## Persisted microphone controls

The reference set Android user-0 restriction `no_unmute_microphone=1`. Audio inspection showed `FromRestrictions=true` and system mute true. It did not establish physical microphone disconnection: a hardware-switch mute was not observed. Keep a physical microphone switch off if present.

The privacy scope clears the secure assistant/voice-service settings and sets these global switches to zero:

```text
receive_explicit_user_interaction_audio_enabled
hotword_detection_enabled
tcl_app_ssm_switch
tcl_app_ssm_cidclient_start
userAgreementCheckboxShareDiagnostics
userAgreementCheckboxTermsExperience
tcl_diagnostic_status
tcl_uxp_status
```

Their names and behavior are firmware-specific. Persisted settings are distinct from enforced physical isolation or a packet-level network audit. Factory reset, firmware replacement, a privileged change or a new app installation can invalidate the recorded configuration.

## Recording AppOps (optional `microphones` scope)

The tool restricts five recording operations for installed app UIDs >=10000 and debugging shell UID 2000. It preserves core UIDs, including 1000, 1002, 1068 and 1073:

```text
RECORD_AUDIO
RECORD_AUDIO_OUTPUT
PHONE_CALL_MICROPHONE
RECEIVE_SOUNDTRIGGER_AUDIO
RECEIVE_EXPLICIT_USER_INTERACTION_AUDIO
```

This can disable voice input in retained apps. The reference independently checked recording denial for its retained apps after setup. The generic tool does not install a boot enforcement module or automatically process future apps. Re-audit after installing or reinstalling apps; Android may allocate different UIDs.

## Content recognition and Alexa

The profile targets these `com.tcl.ttvs` components:

```text
com.tcl.ttvs.ssm.frameserver.SambaVideoService
com.tcl.ttvs.ssm.receiver.SSMReceive
com.tcl.ttvs.alexa.core.AlexaService
```

It uses `pm disable --user 0` for individual components. An earlier attempt with `disable-user` did not produce the intended component state; always verify actual overrides after reboot. The TTvs package stays enabled because it shares core TV functionality. In the reference, disabled components persisted and the Samba service was absent from running services after reboot.

## Debloat scope

`profiles/t653t01-v643.json` lists 18 optional voice, streaming, casting, feedback and helper packages. They are candidates, not a universal removal list. The tool skips missing packages, core/shared UIDs and packages named in `keep_packages`. It uses `pm disable-user`; APKs and data are retained.

Core networking, audio, inputs, package installation, WebView, Play services, Google Services Framework and system update services were retained. No blanket router/DNS blocking or kernel/swap tweaks are part of this toolkit. No performance gain was measured in the reference configuration.

## Plan, apply, verify and undo

Plans collect baseline state and print mutations without applying them. Applying requires an explicit `--apply`, target match, boot completion, root and unchanged baseline. All baseline data stays under `.local/`. A `rollback.sh` is created before the first write, and progress is saved after every command; a interrupted batch may be partially applied.

Inspect the saved script before copying it to the TV and executing it as root. It checks serial, fingerprint and the complete package UID map before restoring original modes. If the UID map changed, review UID operations manually rather than removing that guard. Do not reuse a rollback on another TV.

After applying, check microphone mute, user restrictions, global flags, component overrides, AppOps and your retained apps. Repeat those checks after a deliberate normal reboot. Restoring microphone/ACR defaults removes those protections. Do not claim that these controls block every proprietary collection path.
