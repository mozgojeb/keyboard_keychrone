"""Firmware flash wizard (Tk): one window, home panel then progress panel."""

from __future__ import annotations

import queue
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import tkinter as tk

from . import i18n
from . import firmware_flash as flash
from .theme import apply_theme, MUTED, TEXT


def open_flash_wizard(app, *, parent=None):
    """Tray entry: single window — home (pick .bin) → progress (wait DFU + flash)."""
    root = tk.Toplevel(parent) if parent is not None else tk.Tk()
    apply_theme(root)
    root.title(i18n.t("flash_window_title"))
    root.resizable(False, False)
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass

    # --- shared state -------------------------------------------------------
    selected_bin: list[Path | None] = [None]
    idle_poll_job: list[str | None] = [None]
    progress_poll_job: list[str | None] = [None]
    connected_poll_job: list[str | None] = [None]
    drivers_prompted = [False]
    progress_q: queue.Queue = queue.Queue()
    flash_abort = threading.Event()
    flash_ui: dict = {"phase": "wait_bootloader", "detail": None, "percent": None}
    flash_worker: list[threading.Thread | None] = [None]
    flash_result: list[tuple[bool, str] | None] = [None]
    last_success_after_flash = [False]

    # --- home panel ---------------------------------------------------------
    home = ttk.Frame(root, padding=16)
    lbl_h_status = ttk.Label(home, wraplength=360, font=("", 10, "bold"))
    lbl_h_detail = ttk.Label(home, wraplength=360, foreground=MUTED)
    info_frame = ttk.Frame(home)
    lbl_device = ttk.Label(info_frame, wraplength=360, foreground=TEXT)
    lbl_usb_layout = ttk.Label(info_frame, wraplength=360, foreground=MUTED)
    lbl_firmware = ttk.Label(info_frame, wraplength=360, foreground=TEXT)
    file_frame = ttk.Frame(home)
    lbl_file = ttk.Label(file_frame, wraplength=340, foreground=MUTED)
    btn_choose = ttk.Button(file_frame)
    btn_flash = ttk.Button(file_frame)
    btn_h_drivers = ttk.Button(home)
    btn_h_close = ttk.Button(home)

    # --- progress panel -----------------------------------------------------
    prog = ttk.Frame(root, padding=16)
    lbl_p_status = ttk.Label(prog, wraplength=360, font=("", 10, "bold"))
    lbl_connected = ttk.Label(prog, wraplength=360, foreground=MUTED)
    lbl_p_detail = ttk.Label(prog, wraplength=360, foreground=MUTED)
    lbl_progress_detail = ttk.Label(prog, wraplength=360, foreground=MUTED)
    progress_bar = ttk.Progressbar(prog, mode="determinate", maximum=100, length=320)
    btn_p_close = ttk.Button(prog)

    def stop_idle_poll() -> None:
        if idle_poll_job[0]:
            try:
                root.after_cancel(idle_poll_job[0])
            except tk.TclError:
                pass
            idle_poll_job[0] = None

    def stop_progress_poll() -> None:
        if progress_poll_job[0]:
            try:
                root.after_cancel(progress_poll_job[0])
            except tk.TclError:
                pass
            progress_poll_job[0] = None

    def stop_connected_poll() -> None:
        if connected_poll_job[0]:
            try:
                root.after_cancel(connected_poll_job[0])
            except tk.TclError:
                pass
            connected_poll_job[0] = None

    def show_home(*, success_after_flash: bool = False) -> None:
        stop_progress_poll()
        prog.grid_remove()
        home.grid(row=0, column=0, sticky="nsew")
        root.title(i18n.t("flash_window_title"))
        last_success_after_flash[0] = success_after_flash
        refresh_home(success_after_flash=success_after_flash)
        if not success_after_flash:
            idle_poll()

    def show_progress(bin_path: Path) -> None:
        stop_idle_poll()
        home.grid_remove()
        prog.grid(row=0, column=0, sticky="nsew")
        flash_abort.clear()
        while True:
            try:
                progress_q.get_nowait()
            except queue.Empty:
                break
        flash_ui["phase"] = "wait_bootloader"
        flash_ui["detail"] = None
        flash_ui["percent"] = None
        apply_progress_ui()
        try:
            root.update_idletasks()
            root.deiconify()
            root.lift()
            root.focus_force()
        except tk.TclError:
            pass

        def worker() -> None:
            try:
                ok, code = flash.flash_firmware(
                    bin_path,
                    on_progress=on_progress,
                    should_abort=flash_abort.is_set,
                )
            except Exception:
                ok, code = False, "flash_failed"
            # Hand completion back to the Tk thread so the result handling and
            # any final UI updates always run on the main loop.
            def _finish() -> None:
                flash_result[0] = (bool(ok), str(code))
                handle_flash_finished()

            try:
                root.after(0, _finish)
            except tk.TclError:
                pass

        flash_worker[0] = threading.Thread(target=worker, daemon=True, name="FirmwareFlash")
        flash_worker[0].start()

    def _update_device_info() -> None:
        model, layout, pid, fw = flash.cable_device_info()
        if model:
            lbl_device.config(text=i18n.t("flash_current_device", model=model))
        else:
            lbl_device.config(text=i18n.t("flash_current_device_unknown"))
        if layout and pid is not None:
            lbl_usb_layout.config(
                text=i18n.t("flash_current_usb_layout", layout=layout, pid=f"0x{pid:04X}")
            )
        else:
            lbl_usb_layout.config(text=i18n.t("flash_current_usb_layout_unknown"))
        if fw:
            lbl_firmware.config(text=i18n.t("flash_current_firmware", version=fw))
        else:
            lbl_firmware.config(text=i18n.t("flash_current_firmware_unknown"))

    def refresh_home(*, success_after_flash: bool = False) -> None:
        if success_after_flash:
            if flash.is_cable_keyboard_connected():
                info_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
                _update_device_info()
                lbl_h_status.config(text=i18n.t("flash_ready_title"))
                lbl_h_detail.config(text=i18n.t("flash_success_return_body"))
                file_frame.grid_remove()
                btn_h_drivers.grid_remove()
                return
            lbl_h_status.config(text=i18n.t("flash_success_title"))
            lbl_h_detail.config(text=i18n.t("flash_success_reconnect_body"))
            info_frame.grid_remove()
            file_frame.grid_remove()
            return

        if not flash.is_cable_keyboard_connected():
            # If the keyboard is already in DFU bootloader mode, allow the user
            # to proceed with the normal flash flow (skip the "wait for cable"
            # gate). Otherwise, show the cable instructions but still let the
            # user pick a .bin file in advance; the Flash button will stay
            # disabled until the cable is actually detected.
            if not flash.is_dfu_bootloader_present():
                drivers_prompted[0] = False
                btn_h_drivers.grid_remove()
                info_frame.grid_remove()
                file_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
                lbl_h_status.config(text=i18n.t("flash_wait_cable_title"))
                lbl_h_detail.config(text=i18n.t("flash_wait_cable_body"))
                if selected_bin[0]:
                    lbl_file.config(text=i18n.t("flash_selected_file", path=selected_bin[0]))
                else:
                    lbl_file.config(text=i18n.t("flash_no_file"))
                btn_flash.state(["disabled"])
                return

        ok, err = flash.check_flash_prerequisites()
        if not ok:
            file_frame.grid_remove()
            info_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
            _update_device_info()
            lbl_h_status.config(text=i18n.t("flash_drivers_missing_title"))
            lbl_h_detail.config(text=i18n.t(f"flash_err_{err}"))
            btn_h_drivers.grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 0))
            if not drivers_prompted[0]:
                drivers_prompted[0] = True
                root.after(100, on_drivers_help)
            return

        btn_h_drivers.grid_remove()
        drivers_prompted[0] = False
        info_frame.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        _update_device_info()
        file_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        lbl_h_status.config(text=i18n.t("flash_ready_title"))
        lbl_h_detail.config(text=i18n.t("flash_ready_body"))
        if selected_bin[0]:
            lbl_file.config(text=i18n.t("flash_selected_file", path=selected_bin[0]))
            btn_flash.state(["!disabled"])
        else:
            lbl_file.config(text=i18n.t("flash_no_file"))
            btn_flash.state(["disabled"])

    def idle_poll() -> None:
        if home.winfo_ismapped():
            refresh_home()
            idle_poll_job[0] = root.after(500, idle_poll)

    def _connected_line() -> str:
        device = flash.connected_device_label()
        if device:
            return i18n.t("flash_connected_line", device=device)
        return i18n.t("flash_connected_none")

    def _connected_poll() -> None:
        # Periodically refresh the "Currently connected" line while the progress
        # window is visible so unplug/DFU transitions are reflected in the UI.
        if not prog.winfo_ismapped():
            stop_connected_poll()
            return
        lbl_connected.config(text=_connected_line())
        try:
            connected_poll_job[0] = root.after(500, _connected_poll)
        except tk.TclError:
            connected_poll_job[0] = None

    def _show_write_progress(visible: bool) -> None:
        if visible:
            lbl_progress_detail.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))
            progress_bar.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        else:
            progress_bar.grid_remove()
            lbl_progress_detail.grid_remove()
            progress_bar.stop()

    def apply_progress_ui() -> None:
        phase = flash_ui["phase"]
        pct = flash_ui["percent"]
        detail = flash_ui["detail"]
        try:
            flash._append_flash_log(
                f"apply_progress_ui: phase={phase}, pct={pct}, detail={detail!r}"
            )
        except Exception:
            pass
        lbl_connected.config(text=_connected_line())

        if phase == "wait_bootloader":
            # While waiting for the bootloader, keep the connected device line
            # in sync with reality (cable unplugged, DFU appearing, etc.).
            if connected_poll_job[0] is None:
                _connected_poll()
            root.title(i18n.t("flash_waiting_window_title"))
            lbl_p_status.config(text=i18n.t("flash_waiting_title"))
            lbl_p_detail.config(text=i18n.t("flash_waiting_body"))
            btn_p_close.state(["!disabled"])
            _show_write_progress(False)
            return

        # Once we transition out of the waiting phase, the progress bar
        # represents the actual flash progress.
        progress_bar.stop()
        progress_bar.config(mode="determinate")
        root.title(i18n.t("flash_flashing_window_title"))
        lbl_p_status.config(text=i18n.t("flash_flashing_title"))

        if phase == "bootloader_found":
            lbl_p_detail.config(text=i18n.t("flash_flashing_body"))
            btn_p_close.state(["disabled"])
            progress_bar["value"] = 0
            _show_write_progress(True)
            lbl_progress_detail.config(text=i18n.t("flash_phase_write_start"))
            return

        if phase == "writing":
            lbl_p_detail.config(text=i18n.t("flash_flashing_body"))
            btn_p_close.state(["disabled"])
            _show_write_progress(True)
            if pct is not None:
                progress_bar["value"] = pct
                lbl_progress_detail.config(text=i18n.t("flash_phase_write_pct", pct=pct))
            else:
                lbl_progress_detail.config(
                    text=detail or i18n.t("flash_phase_write_start")
                )
            return

        if phase == "done":
            lbl_p_detail.config(text=i18n.t("flash_flashing_body"))
            _show_write_progress(True)
            progress_bar["value"] = 100
            lbl_progress_detail.config(text=i18n.t("flash_phase_write_pct", pct=100))

    def drain_progress_queue() -> bool:
        """Drain worker updates.

        Returns True when the flash worker signalled completion. We still
        apply *all* intermediate progress updates before reporting done, so
        the UI can show the final percentage before the wizard returns home.
        """
        finished = False
        while True:
            try:
                msg = progress_q.get_nowait()
            except queue.Empty:
                break
            if msg[0] == "__done__":
                flash_result[0] = (bool(msg[1]), str(msg[2]))
                finished = True
                continue
            flash_ui["phase"] = msg[0]
            flash_ui["detail"] = msg[1]
            flash_ui["percent"] = msg[2]
        return finished

    def progress_poll() -> None:
        if not prog.winfo_ismapped():
            return
        finished = drain_progress_queue()
        apply_progress_ui()
        if finished:
            stop_progress_poll()
            handle_flash_finished()
            return
        progress_poll_job[0] = root.after(200, progress_poll)

    def on_progress(phase: str, detail: str | None, percent: int | None) -> None:
        # dfu-util progress arrives from a worker thread. Schedule the actual
        # UI update onto the Tk main thread so we don't depend on a polling
        # loop to animate the progress bar.
        try:
            flash._append_flash_log(
                f"UI on_progress: phase={phase}, pct={percent}, detail={detail!r}"
            )
        except Exception:
            pass

        def _update() -> None:
            flash_ui["phase"] = phase
            flash_ui["detail"] = detail
            flash_ui["percent"] = percent
            apply_progress_ui()

        try:
            root.after(0, _update)
        except tk.TclError:
            # Window may already be closed.
            pass

    def handle_flash_finished() -> None:
        if flash_result[0] is None:
            return
        ok, code = flash_result[0]
        flash_result[0] = None
        if ok:
            show_home(success_after_flash=True)
            return
        if code == "cancelled":
            show_home()
            return
        err_key = f"flash_err_{code}" if code else "flash_err_flash_failed"
        if err_key not in i18n.TRANSLATIONS.get("en", {}):
            err_key = "flash_err_flash_failed"
        messagebox.showerror(i18n.t("flash_failed_title"), i18n.t(err_key), parent=root)
        show_home()

    def on_choose_file() -> None:
        path = filedialog.askopenfilename(
            parent=root,
            title=i18n.t("flash_choose_file"),
            filetypes=[(i18n.t("flash_file_filter"), "*.bin"), ("All", "*.*")],
        )
        if path:
            selected_bin[0] = Path(path)
            refresh_home()

    def on_drivers_help() -> None:
        messagebox.showinfo(
            i18n.t("flash_drivers_missing_title"),
            i18n.t("flash_drivers_dialog"),
            parent=root,
        )
        webbrowser.open(flash.QMK_TOOLBOX_RELEASES_URL)

    def on_home_flash() -> None:
        if not selected_bin[0]:
            return
        if not messagebox.askokcancel(
            i18n.t("flash_confirm_title"),
            i18n.t("flash_confirm_body"),
            parent=root,
        ):
            return
        show_progress(selected_bin[0])

    def on_progress_close() -> None:
        if flash_ui["phase"] == "wait_bootloader":
            # Only support cancelling while we are still waiting for the
            # bootloader. Once dfu-util is writing, the Close button is
            # disabled and we let the flash complete.
            flash_abort.set()
            # flash_firmware will notice should_abort() and return "cancelled",
            # which the worker hands back to handle_flash_finished via
            # root.after.
            return

    def on_window_close() -> None:
        if prog.winfo_ismapped():
            on_progress_close()
            return
        # After a successful flash, Close simply dismisses the wizard; the user
        # can reopen it from the tray if they want to flash again.
        if last_success_after_flash[0]:
            stop_idle_poll()
            stop_connected_poll()
            root.destroy()
            return
        stop_idle_poll()
        stop_connected_poll()
        root.destroy()

    # --- layout: home -------------------------------------------------------
    lbl_h_status.grid(row=0, column=0, columnspan=2, sticky="w")
    lbl_h_detail.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
    lbl_device.grid(row=0, column=0, sticky="w")
    lbl_usb_layout.grid(row=1, column=0, sticky="w", pady=(2, 0))
    lbl_firmware.grid(row=2, column=0, sticky="w", pady=(2, 0))
    lbl_file.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
    btn_choose.grid(row=1, column=0, sticky="w")
    btn_flash.grid(row=1, column=1, sticky="e", padx=(8, 0))
    btn_h_close.grid(row=6, column=1, sticky="e", pady=(16, 0))

    # --- layout: progress ---------------------------------------------------
    lbl_p_status.grid(row=0, column=0, columnspan=2, sticky="w")
    lbl_connected.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
    lbl_p_detail.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
    btn_p_close.grid(row=5, column=1, sticky="e", pady=(16, 0))

    btn_choose.config(command=on_choose_file)
    btn_flash.config(command=on_home_flash, state="disabled")
    btn_h_close.config(command=on_window_close)
    btn_h_drivers.config(command=on_drivers_help)
    btn_p_close.config(command=on_progress_close)
    root.protocol("WM_DELETE_WINDOW", on_window_close)

    btn_choose.config(text=i18n.t("flash_choose_file"))
    btn_flash.config(text=i18n.t("flash_start"))
    btn_h_close.config(text=i18n.t("flash_close"))
    btn_p_close.config(text=i18n.t("flash_close"))
    btn_h_drivers.config(text=i18n.t("flash_drivers_help"))

    show_home()
    if parent is None:
        root.mainloop()
    return root
