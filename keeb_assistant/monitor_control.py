"""Windows DDC/CI monitor discovery and input-source control (VCP 0x60)."""
from contextlib import contextmanager
import ctypes as c
from ctypes import wintypes as w
import re


class MonitorError(RuntimeError):
    pass


def input_codes(capabilities):
    match = re.search(r'\b60\s*\(([^()]*)\)', capabilities, re.I)
    return list(dict.fromkeys(int(v,16) for v in re.findall(r'\b[0-9A-Fa-f]{1,2}\b',match[1]))) if match else []


def monitor_name(device_id,fallback):
    try:
        import winreg
        parts = device_id.split('#')
        path = f'SYSTEM\\CurrentControlSet\\Enum\\DISPLAY\\{parts[1]}\\{parts[2]}\\Device Parameters'
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,path) as key:
            edid = winreg.QueryValueEx(key,'EDID')[0]
        for offset in (54,72,90,108):
            if edid[offset:offset+5] == b'\x00\x00\x00\xfc\x00':
                return edid[offset+5:offset+18].decode('ascii',errors='replace').strip()
    except (OSError,IndexError,ValueError):
        pass
    return fallback


class MonitorControl:
    def __init__(self):
        self.user = c.WinDLL('user32',use_last_error=True)
        self.api = c.WinDLL('dxva2',use_last_error=True)
        class Physical(c.Structure):
            _fields_ = [('handle',w.HANDLE),('description',w.WCHAR*128)]
        class Info(c.Structure):
            _fields_ = [('size',w.DWORD),('monitor',w.RECT),('work',w.RECT),('flags',w.DWORD),('device',w.WCHAR*32)]
        class Display(c.Structure):
            _fields_ = [('size',w.DWORD),('name',w.WCHAR*32),('description',w.WCHAR*128),
                        ('flags',w.DWORD),('id',w.WCHAR*128),('key',w.WCHAR*128)]
        self.Physical,self.Info,self.Display = Physical,Info,Display
        self.enum_type = c.WINFUNCTYPE(w.BOOL,w.HMONITOR,w.HDC,c.POINTER(w.RECT),w.LPARAM)
        self.user.EnumDisplayMonitors.argtypes = [w.HDC,c.c_void_p,self.enum_type,w.LPARAM]
        self.user.GetMonitorInfoW.argtypes = [w.HMONITOR,c.POINTER(Info)]
        self.user.EnumDisplayDevicesW.argtypes = [w.LPCWSTR,w.DWORD,c.POINTER(Display),w.DWORD]
        self.api.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [w.HMONITOR,c.POINTER(w.DWORD)]
        self.api.GetPhysicalMonitorsFromHMONITOR.argtypes = [w.HMONITOR,w.DWORD,c.POINTER(Physical)]
        self.api.DestroyPhysicalMonitors.argtypes = [w.DWORD,c.POINTER(Physical)]
        self.api.GetCapabilitiesStringLength.argtypes = [w.HANDLE,c.POINTER(w.DWORD)]
        self.api.CapabilitiesRequestAndCapabilitiesReply.argtypes = [w.HANDLE,c.c_void_p,w.DWORD]
        self.api.GetVCPFeatureAndVCPFeatureReply.argtypes = [w.HANDLE,w.BYTE,c.POINTER(w.DWORD),c.POINTER(w.DWORD),c.POINTER(w.DWORD)]
        self.api.SetVCPFeature.argtypes = [w.HANDLE,w.BYTE,w.DWORD]

    @contextmanager
    def physical_monitors(self):
        arrays,monitors = [],[]
        @self.enum_type
        def callback(handle,dc,rect,param):
            info = self.Info(size=c.sizeof(self.Info))
            if not self.user.GetMonitorInfoW(handle,c.byref(info)):
                return True
            display = self.Display(size=c.sizeof(self.Display))
            self.user.EnumDisplayDevicesW(info.device,0,c.byref(display),1)
            count = w.DWORD()
            if not self.api.GetNumberOfPhysicalMonitorsFromHMONITOR(handle,c.byref(count)) or not count.value:
                return True
            array = (self.Physical*count.value)()
            if self.api.GetPhysicalMonitorsFromHMONITOR(handle,count,array):
                arrays.append(array)
                for index,p in enumerate(array):
                    monitors.append(dict(id=f'{display.id or info.device}|{index}',
                                         name=monitor_name(display.id,display.description or p.description),description=p.description,
                                         display=info.device,handle=p.handle))
            return True
        try:
            if not self.user.EnumDisplayMonitors(None,None,callback,0):
                raise MonitorError('Windows could not list monitors.')
            yield monitors
        finally:
            for array in arrays:
                self.api.DestroyPhysicalMonitors(len(array),array)

    def current(self,handle):
        kind,current,maximum = w.DWORD(),w.DWORD(),w.DWORD()
        if not self.api.GetVCPFeatureAndVCPFeatureReply(handle,0x60,c.byref(kind),c.byref(current),c.byref(maximum)):
            raise MonitorError('Monitor did not answer input-source query. Enable DDC/CI in its menu.')
        return current.value

    def capabilities(self,handle):
        length = w.DWORD()
        if not self.api.GetCapabilitiesStringLength(handle,c.byref(length)) or not 1 <= length.value <= 65536:
            return ''
        buffer = c.create_string_buffer(length.value)
        if not self.api.CapabilitiesRequestAndCapabilitiesReply(handle,buffer,length):
            return ''
        return buffer.value.decode('ascii',errors='replace')

    def discover(self):
        result = []
        with self.physical_monitors() as monitors:
            for monitor in monitors:
                item = {k:v for k,v in monitor.items() if k!='handle'}
                try:
                    item['current'] = self.current(monitor['handle'])
                    item['error'] = ''
                except MonitorError as exc:
                    item['current'],item['error'] = None,str(exc)
                item['capabilities'] = self.capabilities(monitor['handle'])
                item['inputs'] = input_codes(item['capabilities'])
                result.append(item)
        return result

    def switch(self,monitor_id,value):
        if not isinstance(value,int) or not 1 <= value <= 255:
            raise MonitorError('Input source must be between 0x01 and 0xFF.')
        with self.physical_monitors() as monitors:
            matches = [m for m in monitors if m['id']==monitor_id]
            if len(matches)!=1:
                raise MonitorError('Saved monitor is unavailable. Refresh monitors and select it again.')
            if not self.api.SetVCPFeature(matches[0]['handle'],0x60,value):
                raise MonitorError('Monitor rejected the source change. Check DDC/CI and the input code.')
        # A switch can disconnect this PC, so readback is not always possible.
        return 'Source-change command sent.'

    def toggle(self,monitor_id,first,second):
        if first == second or any(not isinstance(v,int) or not 1<=v<=255 for v in (first,second)):
            raise MonitorError('Choose two different monitor inputs.')
        with self.physical_monitors() as monitors:
            matches = [m for m in monitors if m['id']==monitor_id]
            if len(matches)!=1:
                raise MonitorError('Monitor unavailable. The shortcut must run on a PC still connected to this monitor.')
            handle = matches[0]['handle']
            current = self.current(handle)
            target = second if current==first else first
            if not self.api.SetVCPFeature(handle,0x60,target):
                raise MonitorError('Monitor rejected the source change. Check DDC/CI.')
            return target


if __name__ == '__main__':
    import json
    print(json.dumps(MonitorControl().discover(),indent=2))
