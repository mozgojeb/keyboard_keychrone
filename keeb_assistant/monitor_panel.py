"""Monitor input selection and global shortcut settings."""
import queue
import threading
import tkinter as tk
from tkinter import ttk
from .monitor_shortcuts import input_label


class MonitorPanel(ttk.Frame):
    def __init__(self,parent,app):
        super().__init__(parent,padding=22)
        self.app = app
        self.service = getattr(app,'monitor_shortcuts',None)
        self.monitors = []
        self.results = queue.Queue()
        self.busy = False
        self.last_status = ''
        cfg = app.config.get('monitor_shortcut',{})
        self.monitor = tk.StringVar(self)
        self.first = tk.StringVar(self)
        self.second = tk.StringVar(self)
        self.shortcut = tk.StringVar(self,cfg.get('shortcut','Ctrl+Insert'))
        self.enabled = tk.BooleanVar(self,cfg.get('enabled',False))
        self.status = tk.StringVar(self,'Detecting monitors…')
        self.columnconfigure(1,weight=1)
        ttk.Label(self,text='Monitor source shortcuts',font=('',16,'bold')).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,16))
        self.monitor_combo = ttk.Combobox(self,textvariable=self.monitor,state='readonly')
        self.first_combo = ttk.Combobox(self,textvariable=self.first,state='readonly')
        self.second_combo = ttk.Combobox(self,textvariable=self.second,state='readonly')
        for row,label,widget in [(1,'Monitor',self.monitor_combo),(2,'First source',self.first_combo),(3,'Second source',self.second_combo),
                                  (4,'Toggle shortcut',ttk.Entry(self,textvariable=self.shortcut))]:
            ttk.Label(self,text=label,width=19).grid(row=row,column=0,sticky='w',pady=8)
            widget.grid(row=row,column=1,sticky='ew',pady=8,padx=(0,14))
        ttk.Button(self,text='Refresh monitors',command=self.refresh).grid(row=1,column=2)
        ttk.Checkbutton(self,text='Enable monitor shortcut while Keyboard Companion runs',variable=self.enabled).grid(row=5,column=0,columnspan=3,sticky='w',pady=10)
        ttk.Label(self,text='Example: Ctrl+Insert. Each press switches between the two selected inputs.').grid(row=6,column=0,columnspan=3,sticky='w')
        ttk.Label(self,text='Ctrl+Insert normally means Copy; enabling this shortcut uses it for monitor switching.').grid(row=7,column=0,columnspan=3,sticky='w',pady=(4,16))
        actions = ttk.Frame(self)
        actions.grid(row=8,column=0,columnspan=3,sticky='w')
        for label,command in [('Save shortcut',self.save),('Toggle source',self.toggle),
                              ('First source',lambda:self.direct(self.first)),('Second source',lambda:self.direct(self.second))]:
            ttk.Button(actions,text=label,command=command).pack(side='left',padx=(0,8))
        ttk.Label(self,textvariable=self.status,wraplength=900).grid(row=9,column=0,columnspan=3,sticky='w',pady=18)
        ttk.Label(self,text='MSI MPG321UX OLED: DisplayPort = 0x0F; USB-C uses the second DP channel, 0x10.\n'
                            'Input names are inferred from the advertised ports. Select a different code if your monitor differs.\n\n'
                            'Source switching can move the display to another computer. This shortcut only works while this PC\n'
                            'still receives the keyboard and can communicate with the monitor. Enable DDC/CI in the monitor menu.',
                  wraplength=900).grid(row=10,column=0,columnspan=3,sticky='w')
        self.monitor_combo.bind('<<ComboboxSelected>>',self.select_monitor)
        self.job = self.after(150,self.poll)
        self.bind('<Destroy>',self.destroyed,add='+')
        if self.service:
            self.refresh()
        else:
            self.status.set('Monitor service unavailable in preview.')

    def destroyed(self,event):
        if event.widget is self:
            self.after_cancel(self.job)

    def work(self,action,kind='status'):
        if self.busy or not self.service:
            return
        self.busy = True
        self.status.set('Reading monitor…' if kind=='monitors' else 'Sending source-change command…')
        results = self.results
        io_lock = self.service.io_lock
        def worker():
            if not io_lock.acquire(blocking=False):
                results.put(('error','Monitor is busy. Retry shortly.'))
                return
            try:
                results.put((kind,action()))
            except Exception as exc:
                results.put(('error',str(exc)))
            finally:
                io_lock.release()
        threading.Thread(target=worker,daemon=True,name='MonitorControl').start()

    def refresh(self):
        if self.service:
            self.work(self.service.backend.discover,'monitors')

    def select_monitor(self,event=None):
        index = self.monitor_combo.current()
        if not 0<=index<len(self.monitors):
            return
        monitor = self.monitors[index]
        cfg = self.app.config.get('monitor_shortcut',{})
        codes = monitor['inputs']
        if not codes:
            self.status.set(monitor.get('error') or 'Monitor does not advertise input-source options.')
        self.options = {f'{input_label(code)} (0x{code:02X})':code for code in codes}
        for combo in (self.first_combo,self.second_combo):
            combo.configure(values=list(self.options))
        first = cfg.get('first',16) if cfg.get('monitor_id')==monitor['id'] else 16
        second = cfg.get('second',15) if cfg.get('monitor_id')==monitor['id'] else 15
        self.first.set(next((label for label,code in self.options.items() if code==first),next(iter(self.options),'')))
        self.second.set(next((label for label,code in self.options.items() if code==second),''))
        current = monitor.get('current')
        if current is not None:
            self.status.set(f"Current source: {input_label(current)} (0x{current:02X}).")

    def settings(self):
        index = self.monitor_combo.current()
        if not 0<=index<len(self.monitors):
            raise ValueError('Select a connected monitor first.')
        first = self.options.get(self.first.get())
        second = self.options.get(self.second.get())
        if first is None or second is None or first==second:
            raise ValueError('Choose two different advertised inputs.')
        return dict(enabled=self.enabled.get(),monitor_id=self.monitors[index]['id'],
                    shortcut=self.shortcut.get().strip(),first=first,second=second)

    def save(self):
        if not self.service:
            return
        try:
            # Disabling must work even if the saved monitor is unplugged.
            settings = self.settings() if self.enabled.get() else dict(self.app.config.get('monitor_shortcut',{}),enabled=False)
            self.service.configure(settings)
            self.app.config['monitor_shortcut'] = settings
            self.app.config.save()
            self.status.set(self.service.status)
        except Exception as exc:
            self.status.set(str(exc))

    def toggle(self):
        if not self.service:
            return
        try:
            cfg = self.settings()
            backend = self.service.backend
            def action():
                code = backend.toggle(cfg['monitor_id'],cfg['first'],cfg['second'])
                return f'Source-change command sent: {input_label(code)}.'
            self.work(action)
        except Exception as exc:
            self.status.set(str(exc))

    def direct(self,variable):
        if not self.service:
            return
        try:
            cfg = self.settings()
            code = self.options[variable.get()]
            backend = self.service.backend
            self.work(lambda:backend.switch(cfg['monitor_id'],code))
        except Exception as exc:
            self.status.set(str(exc))

    def poll(self):
        if self.service and self.service.status!=self.last_status:
            self.last_status = self.service.status
            if self.last_status:
                self.status.set(self.last_status)
        try:
            kind,result = self.results.get_nowait()
            self.busy = False
            if kind=='monitors':
                self.monitors = result
                self.monitor_combo.configure(values=[f"{m['name']} ({m['display']})" for m in result])
                saved = self.app.config.get('monitor_shortcut',{}).get('monitor_id')
                if result:
                    self.monitor_combo.current(next((i for i,m in enumerate(result) if m['id']==saved),0))
                    self.select_monitor()
                else:
                    self.status.set('No controllable monitors found.')
            else:
                self.status.set(str(result))
        except queue.Empty:
            pass
        self.job = self.after(150,self.poll)
