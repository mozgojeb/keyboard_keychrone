"""Registered Windows hotkey for a configurable monitor-input toggle."""
from copy import deepcopy
import ctypes as c
from ctypes import wintypes as w
import queue
import threading
from .monitor_control import MonitorControl, MonitorError

KEYS = {'INSERT':0x2D,'INS':0x2D,'HOME':0x24,'END':0x23,'PAGEUP':0x21,'PAGEDOWN':0x22,
        'DELETE':0x2E,'DEL':0x2E,'SPACE':0x20,'PAUSE':0x13,'SCROLLLOCK':0x91}
KEYS.update({f'F{i}':0x6F+i for i in range(1,25)})
KEYS.update({chr(i):i for i in list(range(48,58))+list(range(65,91))})
MODIFIERS = {'CTRL':2,'CONTROL':2,'ALT':1,'SHIFT':4,'WIN':8}


def parse_shortcut(text):
    parts = [part.strip().upper() for part in text.split('+')]
    if not parts or parts[-1] not in KEYS or any(p not in MODIFIERS for p in parts[:-1]):
        raise MonitorError('Use a shortcut such as Ctrl+Insert, Ctrl+Alt+1, or F12.')
    mods = 0
    for part in parts[:-1]:
        mods |= MODIFIERS[part]
    if not mods and parts[-1] not in {f'F{i}' for i in range(1,25)}:
        raise MonitorError('Use a modifier key with letters or navigation keys.')
    return mods|0x4000,KEYS[parts[-1]]  # MOD_NOREPEAT prevents held-key toggles.


class MonitorShortcuts:
    def __init__(self,backend=None):
        self.backend = backend or MonitorControl()
        self.commands = queue.Queue()
        self.ready = threading.Event()
        self.settings = {}
        self.status = ''
        self.io_lock = threading.Lock()
        self.thread = threading.Thread(target=self.run,daemon=True,name='MonitorHotkey')
        self.thread.start()
        if not self.ready.wait(3):
            raise MonitorError('Monitor shortcut service did not start.')

    def configure(self,settings):
        settings = deepcopy(settings)
        if settings.get('enabled'):
            parse_shortcut(settings['shortcut'])
            if not settings.get('monitor_id') or settings['first']==settings['second']:
                raise MonitorError('Select a monitor and two different inputs.')
        response = queue.Queue(maxsize=1)
        self.commands.put((settings,response))
        c.windll.user32.PostThreadMessageW(self.thread_id,0x8001,0,0)
        try:
            error = response.get(timeout=3)
        except queue.Empty:
            raise MonitorError('Monitor shortcut service did not respond.')
        if error:
            raise MonitorError(error)

    def toggle(self):
        if not self.io_lock.acquire(blocking=False):
            return
        settings = deepcopy(self.settings)
        def worker():
            try:
                target = self.backend.toggle(settings['monitor_id'],settings['first'],settings['second'])
                self.status = f'Source-change command sent: {input_label(target)}.'
            except Exception as exc:
                self.status = str(exc)
            finally:
                self.io_lock.release()
        threading.Thread(target=worker,daemon=True,name='MonitorSourceChange').start()

    def stop(self):
        c.windll.user32.PostThreadMessageW(self.thread_id,0x12,0,0)
        self.thread.join(2)

    def run(self):
        user = c.WinDLL('user32',use_last_error=True)
        self.thread_id = c.windll.kernel32.GetCurrentThreadId()
        user.RegisterHotKey.argtypes = [w.HWND,c.c_int,w.UINT,w.UINT]
        user.UnregisterHotKey.argtypes = [w.HWND,c.c_int]
        user.GetMessageW.argtypes = [c.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]
        user.PeekMessageW.argtypes = [c.POINTER(w.MSG),w.HWND,w.UINT,w.UINT,w.UINT]
        message = w.MSG()
        user.PeekMessageW(c.byref(message),None,0,0,0)  # Create thread message queue.
        active_id,combo = None,None
        self.ready.set()
        try:
            while user.GetMessageW(c.byref(message),None,0,0)>0:
                if message.message==0x312 and message.wParam==active_id:
                    self.toggle()
                elif message.message==0x8001:
                    while True:
                        try:
                            settings,response = self.commands.get_nowait()
                        except queue.Empty:
                            break
                        try:
                            new_combo = parse_shortcut(settings['shortcut']) if settings.get('enabled') else None
                            if new_combo != combo:
                                new_id = 2 if active_id==1 else 1
                                if new_combo and not user.RegisterHotKey(None,new_id,*new_combo):
                                    raise MonitorError('Shortcut is already used by another app. Choose a different shortcut.')
                                if active_id:
                                    user.UnregisterHotKey(None,active_id)
                                active_id = new_id if new_combo else None
                                combo = new_combo
                            self.settings = settings
                            self.status = f"{settings.get('shortcut','')} enabled for monitor switching." if new_combo else 'Monitor shortcut disabled.'
                            response.put(None)
                        except Exception as exc:
                            response.put(str(exc))
        finally:
            if active_id:
                user.UnregisterHotKey(None,active_id)


def input_label(code):
    return {15:'DisplayPort',16:'USB-C / DisplayPort 2',17:'HDMI 1',18:'HDMI 2'}.get(code,f'Input 0x{code:02X}')
