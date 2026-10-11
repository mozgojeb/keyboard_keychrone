"""Selectable K10 HE ISO per-key lighting editor."""
from copy import deepcopy
import queue
import re
import threading
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from .keyboard_layout import KEYS
from .lighting_profiles import EFFECTS, KEYPRESS_EFFECTS, load_profiles, normalize_profile, save_profiles


def section_keys(section):
    if section == 'All':
        return {k['led'] for k in KEYS}
    if section == 'Typing':
        return {k['led'] for k in KEYS if k['x'] < 15 and k['row'] > 0}
    if section == 'F-row':
        return set(range(16))
    if section == 'Numpad':
        return {k['led'] for k in KEYS if k['x'] >= 18.5}
    if section == 'Navigation':
        return {k['led'] for k in KEYS if 15 <= k['x'] < 18.5 and k['row'] > 0}
    if section == 'Arrows':
        return {87, 100, 101, 102}
    if section == 'WASD':
        return {39, 59, 60, 61}
    return set()


class LightingEditor(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=14)
        self.app = app
        self.profiles = load_profiles(app.config)
        self.index = next((i for i,p in enumerate(self.profiles)
                           if p['name'] == app.config.get('active_lighting_profile')), 0)
        self.selected = set()
        self.colors = {}
        self.boxes = {}
        self.drag_start = None
        self.busy = False
        self.results = queue.Queue()
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        left = ttk.Frame(self)
        left.grid(row=0, column=0, sticky='ns', padx=(0,14))
        ttk.Label(left, text='Lighting profiles').pack(anchor='w', pady=(0,8))
        self.profile_list = tk.Listbox(left, width=19, height=20, exportselection=False)
        self.profile_list.pack(fill='both', expand=True)
        for label, callback in [('New profile', self.add_profile), ('Duplicate', self.duplicate), ('Delete', self.delete)]:
            ttk.Button(left, text=label, command=callback).pack(fill='x', pady=(6,0))

        editor = ttk.Frame(self)
        editor.grid(row=0, column=1, sticky='nsew')
        editor.columnconfigure(0, weight=1)
        ttk.Label(editor, text='K10 HE ISO · Custom key colours', font=('',14,'bold')).grid(row=0, sticky='w')
        ttk.Label(editor, text='Click a key, Ctrl-click to add keys, or drag a box. Select a section for quick colouring.').grid(row=1, sticky='w', pady=(6,8))
        sections = ttk.Frame(editor)
        sections.grid(row=2, sticky='ew', pady=(0,8))
        for section in ('All','Typing','F-row','Numpad','Navigation','Arrows','WASD','Clear'):
            ttk.Button(sections, text=section, width=10 if section == 'Navigation' else 7,
                       command=lambda name=section: self.select_section(name)).pack(side='left', padx=(0,3))
        self.canvas = tk.Canvas(editor, height=275, background='#141923', highlightthickness=0)
        self.canvas.grid(row=3, sticky='ew')
        self.canvas.bind('<Configure>', lambda event: self.redraw())
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.drag)
        self.canvas.bind('<ButtonRelease-1>', self.release)

        paint = ttk.Frame(editor)
        paint.grid(row=4, sticky='ew', pady=10)
        self.selection_text = tk.StringVar(self, 'No keys selected')
        ttk.Label(paint, textvariable=self.selection_text, width=19).pack(side='left')
        self.paint_color = tk.StringVar(self, '#FFFFFF')
        ttk.Entry(paint, textvariable=self.paint_color, width=10).pack(side='left', padx=4)
        ttk.Button(paint, text='Choose colour…', command=self.choose).pack(side='left', padx=4)
        ttk.Button(paint, text='White', command=lambda: self.paint_color.set('#FFFFFF')).pack(side='left', padx=4)
        ttk.Button(paint, text='Colour selected keys', command=self.paint).pack(side='left', padx=4)
        ttk.Label(editor, text='Colours apply to selected keys only. Brightness is shared by all keys.').grid(row=5, sticky='w')

        fields = ttk.Frame(editor)
        fields.grid(row=6, sticky='ew', pady=(12,0))
        fields.columnconfigure(1, weight=1)
        self.name = tk.StringVar(self)
        self.effect = tk.StringVar(self)
        self.brightness = tk.DoubleVar(self)
        self.speed = tk.DoubleVar(self)
        self.keypress = tk.StringVar(self,'None')
        self.keypress_color = tk.StringVar(self,'#FF6030')
        self.keypress_duration = tk.DoubleVar(self,1200)
        self.overlay_status = ''
        self.effect_combo = ttk.Combobox(fields, textvariable=self.effect, values=EFFECTS, state='readonly')
        self.keypress_combo = ttk.Combobox(fields, textvariable=self.keypress, values=KEYPRESS_EFFECTS, state='readonly')
        self.keypress_combo.bind('<<ComboboxSelected>>', self.update_effect_controls)
        overlay_color = ttk.Frame(fields)
        ttk.Entry(overlay_color, textvariable=self.keypress_color, width=12, state='readonly').pack(side='left')
        ttk.Button(overlay_color,text='Choose…',command=self.choose_keypress_color).pack(side='left',padx=8)
        for row, (label, widget) in enumerate([
            ('Profile name', ttk.Entry(fields, textvariable=self.name)),
            ('Base lighting', self.effect_combo),
            ('On keypress', self.keypress_combo),
            ('Keypress colour', overlay_color),
            ('Fade time (ms)', ttk.Spinbox(fields, from_=200, to=3000, increment=100,
                                         textvariable=self.keypress_duration, format='%.0f', state='readonly')),
            ('Brightness', ttk.Scale(fields, from_=0, to=100, variable=self.brightness)),
            ('Effect speed', ttk.Scale(fields, from_=0, to=100, variable=self.speed)),
        ]):
            ttk.Label(fields, text=label, width=15).grid(row=row, column=0, sticky='w', pady=3)
            widget.grid(row=row, column=1, sticky='ew', pady=3)
        actions = ttk.Frame(editor)
        actions.grid(row=7, sticky='w', pady=(10,0))
        ttk.Button(actions, text='Save profile', command=self.save).pack(side='left')
        self.apply_button = ttk.Button(actions, text='Apply to keyboard', command=self.apply)
        self.apply_button.pack(side='left', padx=8)
        ttk.Label(actions, text='Keypress overlay: Cable mode + app running.').pack(side='left')
        self.status = tk.StringVar(self)
        ttk.Label(editor, textvariable=self.status, wraplength=780).grid(row=8, sticky='w', pady=(8,0))
        self.profile_list.bind('<<ListboxSelect>>', self.switch)
        self.load()
        self.poll_job = self.after(100, self.poll)
        self.bind('<Destroy>', self.on_destroy, add='+')

    def on_destroy(self, event):
        if event.widget is self:
            self.after_cancel(self.poll_job)

    def update_effect_controls(self, event=None):
        enabled = self.keypress.get() != 'None'
        if enabled:
            self.effect.set('Static')
        self.effect_combo.configure(state='disabled' if enabled else 'readonly')

    def choose_keypress_color(self):
        color = colorchooser.askcolor(color=self.keypress_color.get(),parent=self)[1]
        if color:
            self.keypress_color.set(color.upper())

    def select_section(self, section):
        self.selected = section_keys(section)
        self.redraw()

    def redraw(self):
        self.canvas.delete('all')
        self.boxes.clear()
        width = max(self.canvas.winfo_width(), 600)
        unit = (width-20)/22.5
        self.canvas.configure(height=round(unit*6.25+20))
        for key in KEYS:
            led = key['led']
            x, y = 10+key['x']*unit, 10+key['y']*unit
            box = (x+2,y+2,x+key['w']*unit-2,y+key['h']*unit-2)
            self.boxes[led] = box
            color = self.colors.get(str(led), '#18D9FF')
            self.canvas.create_rectangle(*box, fill=color, outline='#FFB547' if led in self.selected else '#3A4354',
                                         width=3 if led in self.selected else 1)
            channels = [int(color[i:i+2],16) for i in (1,3,5)]
            ink = '#10151D' if sum(a*b for a,b in zip(channels,(.299,.587,.114))) > 140 else '#FFFFFF'
            label = key['label']
            if unit < 36:
                label = {'Backspace':'Bksp','Enter':'Ent','Shift':'Shft','Pause':'Paus'}.get(label,label)
            self.canvas.create_text((box[0]+box[2])/2,(box[1]+box[3])/2, text=label,
                                    fill=ink, font=('Segoe UI',max(7,round(unit*.22))))
        self.selection_text.set(f'{len(self.selected)} keys selected' if self.selected else 'No keys selected')

    def press(self, event):
        self.drag_start = (event.x,event.y)
        self.drag_previous = set(self.selected) if event.state & 0x4 else set()
        key = next((led for led,(x1,y1,x2,y2) in self.boxes.items()
                    if x1 <= event.x <= x2 and y1 <= event.y <= y2),None)
        self.selected = set(self.drag_previous)
        if key is not None:
            if key in self.selected:
                self.selected.remove(key)
            else:
                self.selected.add(key)
        self.redraw()

    def drag(self, event):
        if self.drag_start is None:
            return
        x,y = self.drag_start
        if abs(event.x-x)+abs(event.y-y) < 5:
            return
        x1,x2 = sorted((x,event.x))
        y1,y2 = sorted((y,event.y))
        self.selected = self.drag_previous | {led for led,(a,b,c,d) in self.boxes.items()
                                              if x1 < c and x2 > a and y1 < d and y2 > b}
        self.redraw()
        self.canvas.create_rectangle(x1,y1,x2,y2,outline='#FFB547',dash=(4,3))

    def release(self, event):
        self.drag_start = None
        self.redraw()

    def choose(self):
        initial = self.paint_color.get()
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',initial):
            initial = '#FFFFFF'
        color = colorchooser.askcolor(color=initial,parent=self)[1]
        if color:
            self.paint_color.set(color.upper())

    def paint(self):
        color = self.paint_color.get().strip().upper()
        if not self.selected:
            self.status.set('Select keys or a section first.')
            return
        if not re.fullmatch(r'#[0-9A-F]{6}',color):
            self.status.set('Enter a colour as #RRGGBB, for example #FFFFFF for white.')
            return
        for led in self.selected:
            self.colors[str(led)] = color
        self.status.set(f'Coloured {len(self.selected)} keys. Save the profile or apply it to the keyboard.')
        self.redraw()

    def capture(self):
        source = dict(self.profiles[self.index])
        source.update(name=self.name.get(),effect=self.effect.get(),brightness=round(self.brightness.get()),
                      speed=round(self.speed.get()),key_colors=dict(self.colors),
                      keypress_effect=self.keypress.get(),keypress_color=self.keypress_color.get(),
                      keypress_duration=round(self.keypress_duration.get()))
        self.profiles[self.index] = normalize_profile(source)

    def refresh_list(self):
        self.profile_list.delete(0,tk.END)
        for profile in self.profiles:
            self.profile_list.insert(tk.END,profile['name'])
        self.profile_list.selection_set(self.index)

    def load(self):
        p = self.profiles[self.index]
        self.name.set(p['name']); self.effect.set(p['effect'])
        self.brightness.set(p['brightness']); self.speed.set(p['speed'])
        self.keypress.set(p.get('keypress_effect','None'))
        self.keypress_color.set(p.get('keypress_color','#FF6030'))
        self.keypress_duration.set(p.get('keypress_duration',1200))
        self.update_effect_controls()
        self.colors = {str(i):p.get('key_colors',{}).get(str(i),p['color'] if i%5 < 3 else p['accent'])
                       for i in range(len(KEYS))}
        self.selected.clear()
        self.refresh_list()
        self.redraw()

    def switch(self, event=None):
        selection = self.profile_list.curselection()
        if selection and selection[0] != self.index:
            self.capture()
            self.index = selection[0]
            self.load()

    def add_profile(self):
        self.capture()
        self.profiles.append(normalize_profile({'name':f'Custom {len(self.profiles)+1}',
                                               'color':'#FFFFFF','accent':'#FFFFFF'}))
        self.index = len(self.profiles)-1
        self.load()

    def duplicate(self):
        self.capture()
        p = deepcopy(self.profiles[self.index])
        p['name'] = p['name'][:27]+' copy'
        self.profiles.append(p)
        self.index = len(self.profiles)-1
        self.load()

    def delete(self):
        if len(self.profiles) == 1:
            self.status.set('Keep at least one profile.')
            return
        if messagebox.askyesno('Delete profile',f"Delete {self.profiles[self.index]['name']}?",parent=self):
            self.profiles.pop(self.index)
            self.index = min(self.index,len(self.profiles)-1)
            self.load()
            self.save()

    def save(self):
        self.capture()
        save_profiles(self.app.config,self.profiles,self.profiles[self.index]['name'])
        self.refresh_list()
        self.status.set('Profile saved, including every key colour.')

    def apply(self):
        if self.busy:
            return
        self.save()
        profile = deepcopy(self.profiles[self.index])
        self.busy = True
        self.apply_button.state(['disabled'])
        self.status.set('Applying colours…')
        # The worker never holds Tk widgets or variables. Results are polled by Tk.
        results, writer = self.results, self.app.apply_lighting_profile
        def worker():
            try:
                count = writer(profile)
                if profile.get('keypress_effect','None') != 'None':
                    results.put(f"Static + {profile['keypress_effect']} active. Keep Cable mode and the app running; click Apply after restarting the app.")
                else:
                    results.put(f"Applied {profile['name']} to {count} keys and saved it on the keyboard.")
            except Exception as exc:
                results.put(str(exc))
        threading.Thread(target=worker,daemon=True,name='LightingApply').start()

    def poll(self):
        overlay = getattr(self.app,'lighting_overlay',None)
        if overlay and overlay.status and overlay.status != self.overlay_status:
            self.overlay_status = overlay.status
            self.status.set(overlay.status)
        try:
            self.status.set(self.results.get_nowait())
            self.busy = False
            self.apply_button.state(['!disabled'])
        except queue.Empty:
            pass
        self.poll_job = self.after(100,self.poll)
