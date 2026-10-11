# Keyboard Companion

> **For now: complete features on the Keychron K10 HE only.** Several features
> still work on other keyboards (Bluetooth battery, firmware flashing) - see below!

A small, extensible companion app for Keychron keyboards. A Windows **tray** utility
that, at a glance, lets you:

- **See your keyboard's model and battery** in the tray (the model + the raw-HID
  battery over cable/dongle need the modified QMK firmware - see
  [Requirements](#requirements); the model also shows over Bluetooth from Windows).
- **Keep an eye on the charge across all three connections** -> USB cable, 2.4 GHz
  dongle and Bluetooth - with an optional **charging-time correction** so the
  percentage isn't inflated while the keyboard is charging.
- **Flash firmware** straight from the app -> a built-in `dfu-util` wizard that
  generally works for any QMK/DFU keyboard, not just the K10 HE.

Battery reading works over **all three connections**:
- **USB cable** : raw-HID pull,
- **2.4 GHz dongle** : raw-HID push (firmware sends the battery on its own),
- **Bluetooth** : mirrors the battery level Windows already exposes (BLE Battery
  Service), since the vendor raw-HID channel is not available over BT. Shown only
  while the keyboard is **actively connected** (not just paired), so a powered-off
  keyboard never leaves a stale Bluetooth reading on screen.

It can also open the official Keychron launcher and exposes other customizable
options; and it's designed to grow beyond battery monitoring over time.

> Community project. **Not affiliated with or endorsed by Keychron.** The name
> refers to it being a companion app for your keyboard.
> The name is configurable in `keeb_assistant/__init__.py` (`APP_NAME`, `APP_ID`).

## Previews (software GUI may change)

Battery glyph previews with the percentage below:

![Tray icon states](assets/preview.png)

Tray icon and tooltip screenshot on 2.4 GHz dongle:

<p><img width="327" height="311" alt="Tooltip" src="https://github.com/user-attachments/assets/86612c5c-6b0d-4da9-a20e-32b57af2aabd" /></p>

App Settings:

<p><img width="500" height="480" alt="settings window" src="https://github.com/user-attachments/assets/d47890b5-6b17-4989-9f31-3f59c31311e4" /></p>

Flash firmware (USB connection):

<img width="450" height="350" alt="Flash" src="https://github.com/user-attachments/assets/916df15f-2669-4018-a247-e8e5a4b8dbfc" />


## Features

> Per-version changes are on the
> [**Releases**](https://github.com/OutersGIT/keyboard-companion/releases) page.
- Tray icon with the **battery percentage** and color by level (green/amber/red).
- Tooltip with the **connected keyboard's name** (when available), **%, voltage,
  charging state, link type**.
- **Connected device name** in the tooltip across all three links: on **cable**
  it reads the keyboard's own USB product string (works for any Keychron board),
  on the **2.4 GHz dongle** it uses the model id reported by the modified firmware
  (the dongle only exposes its own generic name otherwise), and on **Bluetooth**
  it uses the friendly name Windows shows for the connected device.
- **Smoothing** (EMA + hysteresis) plus an on-battery anti-spike gate, so noisy
  low-charge voltage jumps do not make the tray flicker upward.
- **Charging-% correction**: while charging, the battery voltage is inflated, so
  the keyboard's own percentage overestimates the true charge. The app
  compensates it host-side with an adaptive voltage offset so the shown value
  tracks the resting level (toggleable). A guarded full-charge rule only snaps
  to 100% after a credible high-voltage full state persists.
- **Low-battery notification** (configurable threshold).
- **Optional battery logging** (diagnostics): opt-in CSV in `%APPDATA%` to gather
  real voltage/charging data (used to refine the charging-% correction). Off by
  default; never affects what is displayed.
- **Multi-language UI**: English / Italian / 中文, switchable at runtime and easy
  to extend (see `i18n.py`).
- **Settings window** (language, threshold, notifications, smoothing, charging
  correction, logging, autostart).
- **Main multi-tab window**: the app now opens a single Keyboard Companion
  window with Device, Lighting, Firmware, Settings, and About tabs. Device shows the
  currently connected keyboard details in a table; Firmware currently launches
  the dedicated flash wizard while that workflow is migrated in-place.
- **Lighting profiles**: create, duplicate, delete, save, and switch RGB profiles.
  Applying a profile writes its effect, primary/accent colors, and brightness to
  every addressable LED through Keychron's RGB raw-HID protocol, then saves it to
  keyboard EEPROM. Use Cable mode when applying profiles.
- **Open Launcher** menu entry that opens the official Keychron web launcher in
  your browser.
- **Optional** start-with-Windows, toggleable from the menu or settings.
- **Single tray instance** on Windows (a second launch exits quietly if one is already running).
- **Stable Windows tray identity**: rebuilt executables keep the same notification
  GUID, so Windows should preserve the taskbar-corner visibility preference
  instead of creating a fresh "Keyboard Companion" entry for every build.
- **Windows tray cleanup tools** in Settings: remove stale tray records left by
  old builds and mark the current tray icon as always visible.
- **Stable tray rendering**: the app only re-serializes the tray icon when its
  visible state changes, reducing native PIL/pystray churn during long sessions.
- **Flash firmware…** wizard (tray menu): pick a `.bin`, confirm, then it guides you
  through entering the STM32 DFU bootloader (it shows the live "currently connected"
  state while waiting) and flashes via `dfu-util` with a **real-time progress bar**,
  returning to the home screen with the updated firmware info when done. The
  Windows build bundles QMK's `dfu-util`; the STM32 bootloader still needs the
  WinUSB driver, installable from QMK Toolbox.
- Auto-reconnect when switching cable ⇄ dongle or powering the keyboard back on.

## Requirements
- A Keychron K10 HE flashed with QMK firmware modified to report battery over
  the custom raw-HID channel (command `0xA4`, plus the 2.4 GHz push model) ->
  see the firmware repo
  **[k10he-battery-firmware](https://github.com/OutersGIT/k10he-battery-firmware)**.
  Without that firmware there is no HID battery data over cable/dongle; the
  Bluetooth reading still works, since it mirrors what Windows already exposes.
- Python 3.9+ (only to run from source or to build the exe).

## Download (Windows)

Grab the latest versioned **`KeyboardCompanion-vX.Y.Z-win64.zip`** from the
[**Releases**](https://github.com/OutersGIT/keyboard-companion/releases)
page, extract it to a folder you keep (e.g. `C:\Tools\KeyboardCompanion\`),
then run **`KeyboardCompanion.exe`** inside that folder. The tray icon appears;
right-click it for the menu, or double-click the icon to open the main app window.

Keep the **whole extracted folder** together: do not move or delete the DLLs
and other files next to the exe.

> The battery reading over **cable / 2.4 GHz dongle** requires the modified QMK
> firmware (see [Requirements](#requirements)). The **Bluetooth** reading works
> out of the box, since it mirrors what Windows already reports.

> **Antivirus / trust.** The Windows build is an **unsigned** [PyInstaller](https://pyinstaller.org/)
> **onedir** app (a folder with the exe and its runtime files -> no single-file
> self-extractor). That layout is much less likely to trip ML heuristics than the
> old one-file packer style, but a few scanners may still flag unsigned binaries.
> Since the project is open source you can verify it yourself: scan the zip on
> [VirusTotal](https://www.virustotal.com/),
> [build it yourself](#build-for-windows), or
> [run it from source](#run-from-source).

Devs can run from source or rebuild -> see
[Run from source](#run-from-source) and [Build for Windows](#build-for-windows).

## Run from source
```powershell
cd keeb_assistant
pip install -r requirements.txt
python -m keeb_assistant            # launch the tray app
python -m keeb_assistant --start-in-tray  # launch tray-only, without opening the window
python -m keeb_assistant --once     # print one reading and exit (debug)
```

## Build for Windows
```powershell
.\build_exe.ps1            # dist\KeyboardCompanion\ + dist\KeyboardCompanion-v<version>-win64.zip
```
No Python needed on the target PC. Extract the zip (or copy the folder), run
`KeyboardCompanion.exe` inside it. Right-click the tray icon → Quit to exit.

## Interface and battery widget

The main window, settings, and firmware wizard use the EmblemaShot dark palette.
`keeb_assistant/theme.py` holds their shared Tk colours and control styling.

`KeyboardBatteryWidget.ps1` is the optional matching desktop widget. It reads
`%APPDATA%\KeyboardCompanion\battery_log.csv`; enable **Battery logging** in
Settings first. `LaunchKeyboardBatteryWidget.vbs` starts the widget without a
console window. Keep both files together and run the launcher to show it.

## Autostart (optional)
Off by default. Toggle it from the tray menu or the settings window. It adds or
removes an entry under `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` pointing
at the **current** executable with `--start-in-tray`, so Windows logon starts only
the tray icon and does not open the main window. The tray checkbox is only checked
when that entry exists, matches this install, and the target file is still on disk.
On each app start, if autostart is enabled in config, the Run value is refreshed
(covers renames, moves, and new downloads); stale orphan keys are removed when
autostart is off.

## Configuration
JSON file at `%APPDATA%\KeyboardCompanion\config.json` (created on first run):
- `language` (`en` / `it` / `zh`)
- `smoothing_alpha` (0–1, lower = steadier/slower)
- `smoothing_deadband` (percentage points of hysteresis before the shown value moves)
- `low_battery_threshold` (% below which it notifies)
- `notify_low_battery` (true/false)
- `pull_interval_sec` (how often to poll in cable mode)
- `charge_correction` (true/false — compensate the inflated voltage while charging)
- `charge_offset_mv` (base mV subtracted from the charging voltage before mapping
  to %; the app ramps this upward at high charge based on logged data)
- `battery_logging` (true/false — opt-in CSV diagnostics in `%APPDATA%`)

## Add a language
Edit `keeb_assistant/i18n.py`: add a dict to `TRANSLATIONS` and an entry to
`LANGUAGES`. Missing keys fall back to English automatically.

## Project layout
```
keeb_assistant/
  keeb_assistant/
    hid_reader.py       # unified HID read (dongle push + cable pull)
    ble_reader.py       # Bluetooth battery mirror (Windows PnP property)
    smoothing.py        # EMA + hysteresis
    battery_model.py    # charging-% correction (voltage compensation)
    battery_log.py      # opt-in CSV diagnostics
    icon.py             # battery icon drawing
    i18n.py             # translations (en/it/zh, extensible)
    config.py           # JSON config
    autostart.py        # Windows autostart (registry)
    single_instance.py  # one tray instance (Windows mutex)
    firmware_flash.py   # cable detection + dfu-util flash
    flash_window.py     # flash wizard (Tk)
    main_window.py      # main multi-tab app window
    settings_window.py  # Tk settings window
    tray_registry.py    # Windows tray icon registry tools
    tray_app.py         # tray app (pystray)
    __main__.py         # entry + CLI flags
  run_tray.py           # entry for running/packaging
  build_exe.ps1         # PyInstaller build
  requirements.txt
```
