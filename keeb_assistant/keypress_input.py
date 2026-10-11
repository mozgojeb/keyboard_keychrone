"""Transient physical-key events from the K10 HE USB device only.

Uses Windows Raw Input. No text conversion, key history, disk logging, input
suppression, or network communication. Fn is handled inside the keyboard and
does not emit a Windows key event.
"""
import ctypes as c
from ctypes import wintypes as w
import os
import threading

# IBM set-1 scan codes, including extended navigation/numpad distinctions.
SCAN_LEDS = {1:0,14:29,15:37,28:50,29:92,41:16,42:74,43:70,54:86,56:94,
             57:95,58:58,69:33,70:14,71:54,72:55,73:56,74:36,
             75:71,76:72,77:73,78:57,79:88,80:89,81:90,82:103,83:104,
             86:75,87:11,88:12,55:35}
SCAN_LEDS.update({scan:17+i for i,scan in enumerate(range(2,14))})
SCAN_LEDS.update({scan:38+i for i,scan in enumerate(range(16,28))})
SCAN_LEDS.update({scan:59+i for i,scan in enumerate(range(30,41))})
SCAN_LEDS.update({scan:76+i for i,scan in enumerate(range(44,54))})
SCAN_LEDS.update({scan:1+i for i,scan in enumerate(range(59,69))})
EXTENDED_LEDS = {28:91,29:99,53:34,55:13,56:96,71:31,72:87,73:32,
                 75:100,77:102,79:52,80:101,81:53,82:30,83:51,91:93,93:98}


def key_led(device_name, scan, flags, vkey=0):
    if 'VID_3434&PID_0EA1' not in device_name.upper() or flags & 1:
        return None
    if vkey == 0x13:  # Pause has an E1 sequence.
        return 15
    return (EXTENDED_LEDS if flags & 2 else SCAN_LEDS).get(scan)


class KeypressInput:
    def __init__(self, callback):
        self.callback = callback
        self.ready = threading.Event()
        self.error = None
        self.thread_id = None
        self.thread = threading.Thread(target=self.run, daemon=True, name='KeypressLightingInput')

    def start(self):
        self.thread.start()
        if not self.ready.wait(3):
            raise RuntimeError('Keyboard event listener did not start.')
        if self.error:
            raise RuntimeError(self.error)

    def stop(self):
        if self.thread_id:
            c.windll.user32.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
        if self.thread.is_alive() and threading.current_thread() is not self.thread:
            self.thread.join(2)

    def run(self):
        user = c.WinDLL('user32', use_last_error=True)
        kernel = c.WinDLL('kernel32', use_last_error=True)
        proc_type = c.WINFUNCTYPE(c.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        class WindowClass(c.Structure):
            _fields_ = [('style',w.UINT),('proc',proc_type),('extra',c.c_int),('window_extra',c.c_int),
                        ('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),
                        ('background',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
        class Device(c.Structure):
            _fields_ = [('page',w.USHORT),('usage',w.USHORT),('flags',w.DWORD),('target',w.HWND)]
        class Header(c.Structure):
            _fields_ = [('type',w.DWORD),('size',w.DWORD),('device',w.HANDLE),('param',w.WPARAM)]
        class Keyboard(c.Structure):
            _fields_ = [('scan',w.USHORT),('flags',w.USHORT),('reserved',w.USHORT),
                        ('vkey',w.USHORT),('message',w.UINT),('extra',w.ULONG)]

        user.DefWindowProcW.argtypes = [w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        user.DefWindowProcW.restype = c.c_ssize_t
        user.RegisterClassW.argtypes = [c.POINTER(WindowClass)]
        user.RegisterClassW.restype = w.ATOM
        user.CreateWindowExW.argtypes = [w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,
                                         w.HWND,w.HMENU,w.HINSTANCE,c.c_void_p]
        user.CreateWindowExW.restype = w.HWND
        user.GetRawInputData.argtypes = [w.HANDLE,w.UINT,c.c_void_p,c.POINTER(w.UINT),w.UINT]
        user.GetRawInputData.restype = w.UINT
        user.GetRawInputDeviceInfoW.argtypes = [w.HANDLE,w.UINT,c.c_void_p,c.POINTER(w.UINT)]
        user.GetRawInputDeviceInfoW.restype = w.UINT
        user.RegisterRawInputDevices.argtypes = [c.POINTER(Device),w.UINT,w.UINT]
        user.RegisterRawInputDevices.restype = w.BOOL
        user.GetMessageW.argtypes = [c.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]
        user.GetMessageW.restype = w.BOOL
        user.DispatchMessageW.argtypes = [c.POINTER(w.MSG)]
        user.DispatchMessageW.restype = c.c_ssize_t
        user.DestroyWindow.argtypes = [w.HWND]
        user.UnregisterClassW.argtypes = [w.LPCWSTR,w.HINSTANCE]
        kernel.GetModuleHandleW.restype = w.HMODULE
        instance = kernel.GetModuleHandleW(None)
        self.thread_id = kernel.GetCurrentThreadId()
        names = {}

        def process(handle):
            size = w.UINT()
            if user.GetRawInputData(handle,0x10000003,None,c.byref(size),c.sizeof(Header)) == 0xFFFFFFFF:
                return
            if size.value < c.sizeof(Header)+c.sizeof(Keyboard) or size.value > 4096:
                return
            buffer = c.create_string_buffer(size.value)
            if user.GetRawInputData(handle,0x10000003,buffer,c.byref(size),c.sizeof(Header)) == 0xFFFFFFFF:
                return
            header = Header.from_buffer_copy(buffer)
            if header.type != 1:
                return
            if header.device not in names:
                length = w.UINT(1024)
                name = c.create_unicode_buffer(1024)
                if user.GetRawInputDeviceInfoW(header.device,0x20000007,name,c.byref(length)) == 0xFFFFFFFF:
                    return
                names[header.device] = name.value
            key = Keyboard.from_buffer_copy(buffer,c.sizeof(Header))
            led = key_led(names[header.device],key.scan,key.flags,key.vkey)
            if led is not None:
                self.callback(led)

        @proc_type
        def procedure(hwnd,message,wp,lp):
            if message == 0xFF:
                try:
                    process(lp)
                except Exception:
                    pass
            return user.DefWindowProcW(hwnd,message,wp,lp)

        name = f'KeyboardCompanionLighting_{os.getpid()}_{id(self)}'
        wc = WindowClass(proc=procedure,instance=instance,name=name)
        hwnd = None
        registered = False
        try:
            if not user.RegisterClassW(c.byref(wc)):
                raise c.WinError(c.get_last_error())
            registered = True
            hwnd = user.CreateWindowExW(0,name,'',0,0,0,0,0,w.HWND(-3),None,instance,None)
            if not hwnd:
                raise c.WinError(c.get_last_error())
            device = Device(1,6,0x100,hwnd)  # INPUTSINK, without suppressing normal input.
            if not user.RegisterRawInputDevices(c.byref(device),1,c.sizeof(Device)):
                raise c.WinError(c.get_last_error())
            self.ready.set()
            message = w.MSG()
            while user.GetMessageW(c.byref(message),None,0,0) > 0:
                user.DispatchMessageW(c.byref(message))
        except Exception as exc:
            self.error = str(exc)
            self.ready.set()
        finally:
            device = Device(1,6,1,None)  # RIDEV_REMOVE
            user.RegisterRawInputDevices(c.byref(device),1,c.sizeof(Device))
            if hwnd:
                user.DestroyWindow(hwnd)
            if registered:
                user.UnregisterClassW(name,instance)
