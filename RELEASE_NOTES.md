# Release Notes

## v1.5.0

- Matched the main window, settings, and firmware wizard to EmblemaShot's dark charcoal and cyan interface.
- Updated the optional desktop battery widget to use the same palette.
- Kept keyboard lighting colours and battery warning colours independent of the interface theme.

## v1.4.0

- Added a Monitor tab with DDC/CI discovery, current input, direct source buttons, and a configurable global toggle shortcut.
- Ctrl+Insert can toggle USB-C and DisplayPort on the connected MSI MPG321UX OLED. The monitor reports inputs 0x11, 0x12, 0x0F, and 0x10; the USB-C label for its second DP channel (0x10) is inferred from its physical port set. Inputs remain selectable in the UI.
- Shortcut registrations avoid held-key repeats, report conflicts, persist across app restarts, and unregister when the app exits. Ctrl+Insert replaces the usual Copy shortcut while enabled.
- Commands match the saved Windows monitor device identity. Unavailable monitors or failed current-input reads never fall back to changing another display.
- If switching source transfers the keyboard to another computer via KVM, this PC can no longer receive the shortcut. The other computer needs equivalent control, or use the monitor's source selector.

Validation: live DDC/CI capability/current-input queries and 18 automated checks. Tests simulate input changes; physical USB-C switching remains to be verified by the user.

References: [Windows SetVCPFeature](https://learn.microsoft.com/en-us/windows/win32/api/lowlevelmonitorconfigurationapi/nf-lowlevelmonitorconfigurationapi-setvcpfeature), [MSI port specifications](https://www.msi.com/Monitor/MPG-321URX-QD-OLED/Specification), [USB-C input-code variability](https://www.ddcutil.com/faq/).

## v1.3.0

- Added **On keypress: None / Reactive / Splash** alongside static per-key lighting, with a separate colour and fade duration.
- The app blends a temporary glow or expanding splash over the saved base colours and restores them after fading. Animation frames are sent in batches without EEPROM writes.
- Keypress overlays require the K10 HE in **Cable mode**, with Keyboard Companion running. Click **Apply to keyboard** after restarting the app. The static base remains saved on the keyboard.
- Windows Raw Input filters events to the K10 HE USB device. Only transient physical key positions drive the animation; no typed text or key history is stored. Fn is processed by the keyboard and cannot trigger the app overlay.
- Lighting commands target the ISO USB interface explicitly, avoiding competing responses from an attached wireless receiver.
- The firmware's mixed-effect system cycles effects per region rather than compositing two effects on the same keys; overlays therefore run in the app.

## v1.2.0

- Replaced the decorative lighting preview with the selectable K10 HE ISO 105-key layout.
- Added single-key, Ctrl-click, and drag-box selection, plus typing, F-row, numpad, navigation, arrows, and WASD groups.
- Each profile now stores individual key colours. Existing two-colour profiles remain editable.
- Applying a profile checks the keyboard LED map, writes colours, activates Per Key RGB mode, sets global brightness and speed, and saves the settings.
- Kept all application windows on the main Tk thread and included the complete Tk runtime in the Windows package.

To make the numpad white: select **Numpad**, choose **White**, click **Colour selected keys**, then **Apply to keyboard** in Cable mode. Colour other sections the same way. **Static** keeps colours steady; brightness is global. Key legends follow a UK ISO keyboard; regional legends may differ.

Protocol and layout references: [Keychron K10 HE ISO firmware](https://github.com/Keychron/qmk_firmware/tree/2025q3/keyboards/keychron/k10_he/iso), [Keychron RGB protocol](https://github.com/Keychron/qmk_firmware/blob/2025q3/keyboards/keychron/common/rgb/keychron_rgb.c), and [K10 HE VIA definition](https://github.com/Keychron/qmk_firmware/blob/2025q3/keyboards/keychron/k10_he/via_json/k10_he_iso.json).

## v1.0.3

### What's new

- Added full Keychron Q1 HE support in the firmware flasher: ANSI Knob, ISO Knob and JIS Knob cable-mode USB PIDs are now recognized before entering DFU.
- Fixed Q1 HE model naming over USB when the patched firmware reports `model_id = 2`, so the Device view shows "Keychron Q1 HE" on USB as well as Bluetooth and 2.4 GHz.
- Added explicit Windows shutdown/logoff handling for the tray app.
- During Windows session end, Keyboard Companion now accepts shutdown immediately and exits through a fast path that skips slow UI, tray, logging, and device-name refresh work.
- Added lightweight shutdown diagnostics in `%APPDATA%\KeyboardCompanion\shutdown_log.txt`.

## v1.0.2

- Fixed a rare crash when opening the firmware flash wizard from the Firmware tab while the main app window was still open.
- The Firmware tab now closes the main window before launching the dedicated flash wizard, avoiding multiple Tk roots running in separate threads on Windows.
- Added Companion recognition for Q1 HE firmware battery reports, so 2.4 GHz dongle readings can show "Keychron Q1 HE" instead of the generic dongle name when the keyboard firmware reports model id 2.
# 1.1.0

- Added Lighting tab with persistent named RGB profiles.
- Added real Keychron `0xA8` RGB raw-HID writes for effect, per-key colors,
  brightness, and EEPROM save.
- Added Lighting profiles tray shortcut.
- Bundled checksum-verified `dfu-util` from official QMK flashutils release
  20260711, removing the misleading "dfu-util not found" error.
- Fixed `BatteryReader.join()` shutdown error caused by shadowing `Thread._stop`.
