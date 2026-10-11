"""Minimal internationalization.

Add a new language by appending a dict to TRANSLATIONS and an entry to
LANGUAGES. Missing keys fall back to English, missing English falls back to the
key itself, so the app never crashes on a forgotten string.
"""

from __future__ import annotations

DEFAULT_LANGUAGE = "en"

# (code, native label) — order defines the menu/dropdown order.
LANGUAGES = [
    ("en", "English"),
    ("it", "Italiano"),
    ("zh", "中文"),
]

TRANSLATIONS = {
    "en": {
        "no_data": "No data (keyboard off or disconnected)",
        "undetected": "Undetected",
        "charging_0": "Battery Mode",
        "charging_1": "Charging",
        "charging_2": "Fully charged",
        "age_suffix": "  ({sec}s ago)",
        "tooltip_waiting": "waiting…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "tooltip_device_line": "{device}",
        "menu_settings": "Settings…",
        "menu_lighting": "Lighting profiles…",
        "menu_open_launcher": "Open Launcher (web)",
        "menu_autostart": "Start with Windows",
        "menu_notify": "Low-battery notification",
        "menu_flash_firmware": "Flash firmware…",
        "menu_language": "Language",
        "menu_quit": "Quit",
        "main_tab_device": "Device",
        "main_tab_lighting": "Lighting",
        "main_tab_about": "About",
        "main_tab_settings": "Settings",
        "main_tab_firmware": "Firmware",
        "device_tab_title": "Connected device",
        "device_field_model": "Model name",
        "device_field_battery": "Battery",
        "device_field_voltage": "Voltage",
        "device_field_mode": "Mode",
        "device_field_connection": "Connection",
        "device_field_source": "Data source",
        "device_tab_note": "Some fields depend on the connection mode. Bluetooth mirrors Windows battery data, so voltage and charging state may be unavailable.",
        "about_version": "Version {version}",
        "about_body": "Community tray utility for Keychron keyboards. It monitors battery state, manages Windows tray behavior, and helps flash compatible firmware.",
        "firmware_tab_title": "Firmware flashing",
        "firmware_tab_body": "The firmware workflow still opens the dedicated wizard while this tab is being migrated into the main window. The wizard handles bootloader detection, progress, and write protection.",
        "firmware_tab_open_wizard": "Open flash wizard",
        "lighting_title": "Lighting profiles",
        "lighting_add": "New profile",
        "lighting_duplicate": "Duplicate",
        "lighting_delete": "Delete",
        "lighting_name": "Profile name",
        "lighting_effect": "Effect",
        "lighting_primary": "Primary color",
        "lighting_accent": "Accent color",
        "lighting_brightness": "Brightness",
        "lighting_speed": "Effect speed",
        "lighting_save": "Save changes",
        "lighting_apply": "Apply profile",
        "lighting_saved": "Profile saved locally.",
        "lighting_applying": "Applying profile to keyboard…",
        "lighting_applied": "Applied to {count} LEDs and saved on keyboard.",
        "lighting_apply_failed": "Could not apply profile: {error}",
        "notify_low_title": "Low battery",
        "notify_low_body": "Keyboard battery at {pct}%. Plug in the cable to charge.",
        "settings_title": "{app} — Settings",
        "settings_language": "Language",
        "settings_threshold": "Low-battery threshold (%)",
        "settings_notify": "Notify on low battery",
        "settings_smoothing": "Smoothing (lower = steadier)",
        "settings_autostart": "Start automatically with Windows",
        "settings_logging": "Log battery data (diagnostics)",
        "settings_open_log": "Open log folder",
        "settings_charge_correction": "Correct % while charging",
        "settings_tray_tools": "Windows tray icon tools",
        "settings_clean_tray_records": "Delete old Windows tray records",
        "settings_promote_tray_icon": "Set tray icon always visible",
        "settings_clean_tray_done": "Removed {count} old tray record(s). Reopen Windows Settings if the list is still visible.",
        "settings_promote_tray_done": "The current tray icon is set to always visible.",
        "settings_promote_tray_failed": "Could not find the current tray icon record yet. Leave the app running for a few seconds, then retry.",
        "settings_save": "Save",
        "settings_close": "Close",
        "settings_note": "Some changes apply immediately; language updates the menu too.",
        "cli_no_data": "No battery data (keyboard off/disconnected or firmware without support).",
        "cli_line": "Battery: {pct}%  ({mv} mV)  |  State: {charging}  |  Link: {transport}",
        "flash_window_title": "Flash firmware",
        "flash_waiting_window_title": "Waiting for bootloader…",
        "flash_flashing_window_title": "Flashing…",
        "flash_wait_cable_title": "Waiting for keyboard (USB cable)",
        "flash_wait_cable_body": (
            "Set the side switch to Cable, connect the keyboard with USB, and leave "
            "it on. This window updates automatically. If you unplug the cable, the "
            "wizard returns to this step."
        ),
        "flash_drivers_missing_title": "DFU tools or driver missing",
        "flash_drivers_dialog": (
            "Keyboard Companion uses dfu-util (same stack as QMK Toolbox) to flash "
            "the STM32 bootloader.\n\n"
            "Install QMK Toolbox (recommended — it installs the WinUSB driver), or "
            "install dfu-util and bind the STM32 DFU device with Zadig.\n\n"
            "The releases page will open in your browser."
        ),
        "flash_drivers_help": "Driver / QMK Toolbox help…",
        "flash_ready_title": "Keyboard connected",
        "flash_ready_body": (
            "Choose a .bin firmware file, then click Flash. After you confirm, "
            "you will be asked to enter bootloader mode (unplug, hold Esc, replug)."
        ),
        "flash_current_device": "Device: {model}",
        "flash_current_device_unknown": "Device: (unknown)",
        "flash_current_usb_layout": (
            "USB layout (set by flashed firmware): {layout} · PID {pid}"
        ),
        "flash_current_usb_layout_unknown": "USB layout: (could not read)",
        "flash_current_firmware": "Firmware version: {version}",
        "flash_current_firmware_unknown": "Firmware version: (could not read)",
        "flash_choose_file": "Choose file…",
        "flash_no_file": "No file selected.",
        "flash_selected_file": "File: {path}",
        "flash_file_filter": "Firmware binary",
        "flash_start": "Flash",
        "flash_close": "Close",
        "flash_confirm_title": "Flash firmware?",
        "flash_confirm_body": (
            "This will overwrite the keyboard firmware. Only continue if you trust "
            "this .bin file.\n\n"
            "On the next screen: unplug USB, set Cable mode, hold Esc, plug USB back in, "
            "then release Esc. Do not unplug again while the progress bar is writing."
        ),
        "flash_waiting_title": "Waiting for bootloader…",
        "flash_waiting_body": (
            "The flash procedure is running.\n\n"
            "Unplug the USB cable now. Press and hold ESC, then plug the keyboard "
            "back in (side switch on Cable). The actual firmware write will start "
            "once bootloader mode is detected."
        ),
        "flash_flashing_title": "Flashing…",
        "flash_flashing_body": (
            "Keep the USB cable connected while the firmware is written. Do not unplug."
        ),
        "flash_connected_line": "Currently connected: {device}",
        "flash_connected_none": "Currently connected: (none detected yet)",
        "flash_phase_write_pct": "Progress: {pct}%",
        "flash_phase_write_start": "Preparing download…",
        "flash_success_title": "Flash complete",
        "flash_success_body": "The keyboard should reboot into normal mode.",
        "flash_success_return_body": (
            "Flash completed successfully. Check the firmware version above — it should "
            "show the build you just flashed."
        ),
        "flash_success_reconnect_body": (
            "Flash completed. Set the side switch to Cable and plug in USB to return to "
            "the main screen and verify the new firmware version."
        ),
        "flash_failed_title": "Flash failed",
        "flash_err_platform": "Firmware flashing is only supported on Windows.",
        "flash_err_hidapi": "hidapi is not available; reinstall Keyboard Companion.",
        "flash_err_dfu_util": "dfu-util was not found. Install QMK Toolbox or add dfu-util to PATH.",
        "flash_err_dfu_list": "dfu-util did not respond. Install QMK Toolbox and retry.",
        "flash_err_missing_file": "The selected .bin file is missing.",
        "flash_err_bootloader_timeout": (
            "Bootloader not detected in time. Hold Esc while plugging in USB (Cable mode)."
        ),
        "flash_err_cancelled": "Flash cancelled.",
        "flash_err_driver": (
            "dfu-util could not open the device. Install the WinUSB driver via QMK Toolbox."
        ),
        "flash_err_flash_failed": "dfu-util reported an error. See the log and retry.",
    },
    "it": {
        "no_data": "Nessun dato (tastiera spenta o disconnessa)",
        "undetected": "Non rilevata",
        "charging_0": "Modalità batteria",
        "charging_1": "In carica",
        "charging_2": "Carica completa",
        "age_suffix": "  (dato di {sec}s fa)",
        "tooltip_waiting": "in attesa…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "tooltip_device_line": "{device}",
        "menu_settings": "Impostazioni…",
        "menu_open_launcher": "Apri Launcher (web)",
        "menu_autostart": "Avvio automatico con Windows",
        "menu_notify": "Notifica batteria bassa",
        "menu_flash_firmware": "Flash firmware…",
        "menu_language": "Lingua",
        "menu_quit": "Esci",
        "main_tab_device": "Dispositivo",
        "main_tab_about": "Info",
        "main_tab_settings": "Impostazioni",
        "main_tab_firmware": "Firmware",
        "device_tab_title": "Dispositivo connesso",
        "device_field_model": "Nome modello",
        "device_field_battery": "Batteria",
        "device_field_voltage": "Voltaggio",
        "device_field_mode": "Modalita",
        "device_field_connection": "Connessione",
        "device_field_source": "Fonte dati",
        "device_tab_note": "Alcuni campi dipendono dalla modalita di connessione. In Bluetooth viene letto il valore noto a Windows, quindi voltaggio e stato carica possono non essere disponibili.",
        "about_version": "Versione {version}",
        "about_body": "Utility tray community per tastiere Keychron. Monitora la batteria, gestisce il comportamento della tray di Windows e aiuta a flashare firmware compatibili.",
        "firmware_tab_title": "Flash firmware",
        "firmware_tab_body": "Il flusso firmware apre ancora il wizard dedicato mentre questa tab viene migrata nella finestra principale. Il wizard gestisce bootloader, progresso e protezione durante la scrittura.",
        "firmware_tab_open_wizard": "Apri wizard flash",
        "notify_low_title": "Batteria bassa",
        "notify_low_body": "Batteria tastiera al {pct}%. Collega il cavo per ricaricare.",
        "settings_title": "{app} — Impostazioni",
        "settings_language": "Lingua",
        "settings_threshold": "Soglia batteria bassa (%)",
        "settings_notify": "Notifica batteria bassa",
        "settings_smoothing": "Smoothing (più basso = più stabile)",
        "settings_autostart": "Avvia automaticamente con Windows",
        "settings_logging": "Registra dati batteria (diagnostica)",
        "settings_open_log": "Apri cartella log",
        "settings_charge_correction": "Correggi % durante la carica",
        "settings_tray_tools": "Strumenti icona tray di Windows",
        "settings_clean_tray_records": "Elimina vecchie voci tray di Windows",
        "settings_promote_tray_icon": "Mostra sempre l'icona nella tray",
        "settings_clean_tray_done": "Rimosse {count} vecchie voci tray. Riapri le Impostazioni di Windows se la lista era gia aperta.",
        "settings_promote_tray_done": "L'icona tray corrente e impostata come sempre visibile.",
        "settings_promote_tray_failed": "Voce tray corrente non trovata. Lascia l'app aperta per qualche secondo e riprova.",
        "settings_save": "Salva",
        "settings_close": "Chiudi",
        "settings_note": "Alcune modifiche sono immediate; la lingua aggiorna anche il menu.",
        "cli_no_data": "Nessun dato batteria (tastiera spenta/disconnessa o firmware senza supporto).",
        "cli_line": "Batteria: {pct}%  ({mv} mV)  |  Stato: {charging}  |  Connessione: {transport}",
        "flash_window_title": "Flash firmware",
        "flash_waiting_window_title": "In attesa del bootloader…",
        "flash_flashing_window_title": "Flash in corso…",
        "flash_wait_cable_title": "In attesa della tastiera (cavo USB)",
        "flash_wait_cable_body": (
            "Imposta l'interruttore su Cable, collega la tastiera via USB e lasciala accesa. "
            "La finestra si aggiorna da sola. Se scolleghi il cavo, la procedura riparte da qui."
        ),
        "flash_drivers_missing_title": "Tool DFU o driver mancanti",
        "flash_drivers_dialog": (
            "Keyboard Companion usa dfu-util (come QMK Toolbox) per flashare il bootloader STM32.\n\n"
            "Installa QMK Toolbox (consigliato — installa anche il driver WinUSB), oppure "
            "dfu-util e associa il dispositivo DFU con Zadig.\n\n"
            "Si aprirà la pagina delle release nel browser."
        ),
        "flash_drivers_help": "Aiuto driver / QMK Toolbox…",
        "flash_ready_title": "Tastiera collegata",
        "flash_ready_body": (
            "Scegli un file .bin, poi clicca Flash. Dopo la conferma ti verrà chiesto "
            "di entrare in bootloader (stacca, tieni Esc, ricollega)."
        ),
        "flash_current_device": "Dispositivo: {model}",
        "flash_current_device_unknown": "Dispositivo: (sconosciuto)",
        "flash_current_usb_layout": (
            "Layout USB (dal firmware installato): {layout} · PID {pid}"
        ),
        "flash_current_usb_layout_unknown": "Layout USB: (non leggibile)",
        "flash_current_firmware": "Versione firmware: {version}",
        "flash_current_firmware_unknown": "Versione firmware: (non leggibile)",
        "flash_choose_file": "Scegli file…",
        "flash_no_file": "Nessun file selezionato.",
        "flash_selected_file": "File: {path}",
        "flash_file_filter": "Firmware binario",
        "flash_start": "Flash",
        "flash_close": "Chiudi",
        "flash_confirm_title": "Flashare il firmware?",
        "flash_confirm_body": (
            "Sovrascriverà il firmware della tastiera. Continua solo se ti fidi del .bin.\n\n"
            "Nella schermata successiva: stacca USB, interruttore su Cable, tieni Esc, "
            "ricollega USB e rilascia Esc. Non staccare di nuovo mentre la barra scrive."
        ),
        "flash_waiting_title": "In attesa del bootloader…",
        "flash_waiting_body": (
            "La procedura di flash è attiva.\n\n"
            "Stacca il cavo USB. Tieni premuto ESC e ricollega (interruttore su Cable). "
            "La scrittura del firmware partirà quando verrà rilevato il bootloader."
        ),
        "flash_flashing_title": "Flash in corso…",
        "flash_flashing_body": (
            "Tieni il cavo USB collegato durante la scrittura del firmware. Non scollegare."
        ),
        "flash_connected_line": "Attualmente collegato: {device}",
        "flash_connected_none": "Attualmente collegato: (nessun dispositivo rilevato)",
        "flash_phase_write_pct": "Avanzamento: {pct}%",
        "flash_phase_write_start": "Preparazione download…",
        "flash_success_title": "Flash completato",
        "flash_success_body": "La tastiera dovrebbe riavviarsi in modalità normale.",
        "flash_success_return_body": (
            "Flash completato. Controlla la versione firmware sopra — dovrebbe corrispondere "
            "al file appena scritto."
        ),
        "flash_success_reconnect_body": (
            "Flash completato. Imposta Cable e collega USB per tornare alla schermata "
            "principale e verificare il nuovo firmware."
        ),
        "flash_failed_title": "Flash non riuscito",
        "flash_err_platform": "Il flash è supportato solo su Windows.",
        "flash_err_hidapi": "hidapi non disponibile; reinstalla Keyboard Companion.",
        "flash_err_dfu_util": "dfu-util non trovato. Installa QMK Toolbox o aggiungi dfu-util al PATH.",
        "flash_err_dfu_list": "dfu-util non risponde. Installa QMK Toolbox e riprova.",
        "flash_err_missing_file": "Il file .bin selezionato non esiste.",
        "flash_err_bootloader_timeout": (
            "Bootloader non rilevato in tempo. Tieni Esc premuto mentre ricolleghi il USB (Cable)."
        ),
        "flash_err_cancelled": "Flash annullato.",
        "flash_err_driver": (
            "dfu-util non apre il dispositivo. Installa il driver WinUSB con QMK Toolbox."
        ),
        "flash_err_flash_failed": "Errore da dfu-util. Riprova.",
    },
    "zh": {
        "no_data": "无数据（键盘已关闭或未连接）",
        "undetected": "未检测到",
        "charging_0": "电池模式",
        "charging_1": "充电中",
        "charging_2": "已充满",
        "age_suffix": "  （{sec} 秒前）",
        "tooltip_waiting": "等待中…",
        "info_line": "{pct}%  •  {mv} mV  •  {charging}  •  {transport}{age}",
        "info_line_ble": "{pct}%  •  {transport}",
        "tooltip_device_line": "{device}",
        "menu_settings": "设置…",
        "menu_open_launcher": "打开 Launcher（网页）",
        "menu_autostart": "开机自启动",
        "menu_notify": "低电量通知",
        "menu_flash_firmware": "刷写固件…",
        "menu_language": "语言",
        "menu_quit": "退出",
        "notify_low_title": "电量低",
        "notify_low_body": "键盘电量 {pct}%。请插入数据线充电。",
        "settings_title": "{app} — 设置",
        "settings_language": "语言",
        "settings_threshold": "低电量阈值 (%)",
        "settings_notify": "低电量时通知",
        "settings_smoothing": "平滑（越低越稳定）",
        "settings_autostart": "随 Windows 自动启动",
        "settings_logging": "记录电池数据（诊断）",
        "settings_open_log": "打开日志文件夹",
        "settings_charge_correction": "充电时校正百分比",
        "settings_save": "保存",
        "settings_close": "关闭",
        "settings_note": "部分更改即时生效；语言也会更新菜单。",
        "cli_no_data": "无电池数据（键盘关闭/未连接或固件不支持）。",
        "cli_line": "电池：{pct}%（{mv} mV） | 状态：{charging} | 连接：{transport}",
        "flash_window_title": "刷写固件",
        "flash_waiting_window_title": "等待引导程序…",
        "flash_flashing_window_title": "正在刷写…",
        "flash_wait_cable_title": "等待键盘（USB 数据线）",
        "flash_wait_cable_body": (
            "将侧边开关设为 Cable，用 USB 连接键盘并保持开机。"
            "窗口会自动更新；若拔掉线缆，将从头开始。"
        ),
        "flash_drivers_missing_title": "缺少 DFU 工具或驱动",
        "flash_drivers_dialog": (
            "Keyboard Companion 使用 dfu-util（与 QMK Toolbox 相同）刷写 STM32 引导程序。\n\n"
            "请安装 QMK Toolbox（推荐，会安装 WinUSB 驱动），或安装 dfu-util 并用 Zadig 绑定 DFU 设备。\n\n"
            "将在浏览器中打开发布页。"
        ),
        "flash_drivers_help": "驱动 / QMK Toolbox 帮助…",
        "flash_ready_title": "键盘已连接",
        "flash_ready_body": (
            "选择 .bin 固件文件，然后点击刷写。确认后将提示进入引导程序（拔线、按住 Esc、再插入）。"
        ),
        "flash_current_device": "设备：{model}",
        "flash_current_device_unknown": "设备：（未知）",
        "flash_current_usb_layout": "USB 布局（由已刷固件决定）：{layout} · PID {pid}",
        "flash_current_usb_layout_unknown": "USB 布局：（无法读取）",
        "flash_current_firmware": "固件版本：{version}",
        "flash_current_firmware_unknown": "固件版本：（无法读取）",
        "flash_choose_file": "选择文件…",
        "flash_no_file": "未选择文件。",
        "flash_selected_file": "文件：{path}",
        "flash_file_filter": "固件二进制",
        "flash_start": "刷写",
        "flash_close": "关闭",
        "flash_confirm_title": "刷写固件？",
        "flash_confirm_body": (
            "将覆盖键盘固件。请确认信任该 .bin 文件。\n\n"
            "下一步：拔 USB、开关设为 Cable、按住 Esc、插入 USB 后松开 Esc。"
            "进度条写入期间请勿再次拔线。"
        ),
        "flash_waiting_title": "等待引导程序…",
        "flash_waiting_body": (
            "刷写流程已启动。\n\n"
            "请拔下 USB。按住 ESC 后重新插入（开关设为 Cable）。检测到引导程序后将开始写入固件。"
        ),
        "flash_flashing_title": "正在刷写…",
        "flash_flashing_body": "写入固件时请保持 USB 连接，请勿拔线。",
        "flash_connected_line": "当前连接：{device}",
        "flash_connected_none": "当前连接：（尚未检测到设备）",
        "flash_phase_write_pct": "进度：{pct}%",
        "flash_phase_write_start": "准备下载…",
        "flash_success_title": "刷写完成",
        "flash_success_body": "键盘应会重启进入正常模式。",
        "flash_success_return_body": (
            "刷写成功。请查看上方的固件版本，应显示刚写入的构建。"
        ),
        "flash_success_reconnect_body": (
            "刷写完成。请将开关设为 Cable 并插入 USB，返回主界面并确认新固件版本。"
        ),
        "flash_failed_title": "刷写失败",
        "flash_err_platform": "仅支持在 Windows 上刷写固件。",
        "flash_err_hidapi": "hidapi 不可用；请重新安装 Keyboard Companion。",
        "flash_err_dfu_util": "未找到 dfu-util。请安装 QMK Toolbox 或将 dfu-util 加入 PATH。",
        "flash_err_dfu_list": "dfu-util 无响应。请安装 QMK Toolbox 后重试。",
        "flash_err_missing_file": "所选 .bin 文件不存在。",
        "flash_err_bootloader_timeout": "超时未检测到引导程序。插入 USB 时按住 Esc（Cable 模式）。",
        "flash_err_cancelled": "已取消刷写。",
        "flash_err_driver": "dfu-util 无法打开设备。请通过 QMK Toolbox 安装 WinUSB 驱动。",
        "flash_err_flash_failed": "dfu-util 报错。请重试。",
    },
}

_current = DEFAULT_LANGUAGE


def available_languages():
    return list(LANGUAGES)


def set_language(lang: str) -> None:
    global _current
    if lang in TRANSLATIONS:
        _current = lang


def get_language() -> str:
    return _current


def language_label(lang: str) -> str:
    for code, label in LANGUAGES:
        if code == lang:
            return label
    return lang


def t(key: str, **kwargs) -> str:
    text = TRANSLATIONS.get(_current, {}).get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text
