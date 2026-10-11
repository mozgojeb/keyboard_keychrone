"""USB lighting overlay: transient frames, never EEPROM writes."""
from copy import deepcopy
import math
from collections import deque
import threading
import time

from .keyboard_layout import KEYS
from .keypress_input import KeypressInput
from .lighting_hid import _rgb_to_hsv, _request, LightingError

POSITIONS = [(k['x']+k['w']/2,k['y']+k['h']/2) for k in KEYS]


def base_colors(profile):
    return [profile.get('key_colors',{}).get(str(i),profile['color'] if i%5<3 else profile['accent'])
            for i in range(len(KEYS))]


def render_frame(profile, hits, now):
    """Blend a fading key glow or expanding coloured ring over the static map."""
    base = base_colors(profile)
    duration = profile.get('keypress_duration',1200)/1000
    accent = profile.get('keypress_color','#FF6030')
    overlay = tuple(int(accent[i:i+2],16) for i in (1,3,5))
    frame = []
    for index, color in enumerate(base):
        strength = 0.0
        for origin,stamp in hits:
            age = (now-stamp)/duration
            if not 0 <= age < 1:
                continue
            if profile.get('keypress_effect') == 'Reactive':
                amount = (1-age)**2 if index == origin else 0
            else:
                x,y = POSITIONS[index]
                a,b = POSITIONS[origin]
                distance = math.hypot(x-a,y-b)
                radius = age*24
                amount = max(0,1-abs(distance-radius)/2.8)*(1-age)
            strength = max(strength,amount)
        original = tuple(int(color[i:i+2],16) for i in (1,3,5))
        rgb = tuple(round(a+(b-a)*strength) for a,b in zip(original,overlay))
        frame.append('#%02X%02X%02X' % rgb)
    return frame


def write_frame(reader, colors, previous=None, stopped=None):
    """Send up to nine LED colours per report; skip unchanged chunks."""
    for start in range(0,len(colors),9):
        if stopped is not None and stopped.is_set():
            return False
        chunk = colors[start:start+9]
        if previous is not None and chunk == previous[start:start+9]:
            continue
        data = bytes(component for color in chunk for component in _rgb_to_hsv(color,100))
        response = _request(reader,bytes([0xA8,10,start,len(chunk)])+data,subcommand=10,timeout=.2)
        if len(response)<3 or response[2] != 0:
            raise LightingError('Keyboard rejected a keypress lighting frame.')
    return True


class LightingOverlay:
    def __init__(self, reader, listener_factory=KeypressInput):
        self.reader = reader
        self.listener_factory = listener_factory
        self.thread = None
        self.listener = None
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.hits = deque(maxlen=16)
        self.status = ''

    def start(self, profile):
        self.profile = deepcopy(profile)
        self.stopped.clear()
        with self.lock:
            self.hits.clear()
        self.listener = self.listener_factory(self.hit)
        try:
            self.listener.start()
        except Exception:
            self.listener.stop()
            self.listener = None
            raise
        self.status = f"Static + {profile['keypress_effect']} active in Cable mode. Keep Keyboard Companion running."
        self.thread = threading.Thread(target=self.run,daemon=True,name='LightingOverlay')
        self.thread.start()

    def hit(self, led):
        if 0 <= led < len(KEYS) and not self.stopped.is_set():
            with self.lock:
                self.hits.append((led,time.monotonic()))

    def stop(self):
        self.stopped.set()
        if self.listener:
            self.listener.stop()
        if self.thread and self.thread.is_alive():
            self.thread.join(5)
            if self.thread.is_alive():
                raise LightingError('Previous lighting overlay is still stopping. Retry shortly.')
        self.status = ''

    def run(self):
        base = base_colors(self.profile)
        previous = base
        changed = False
        try:
            while not self.stopped.wait(.06):
                now = time.monotonic()
                with self.lock:
                    duration = self.profile['keypress_duration']/1000
                    while self.hits and now-self.hits[0][1] >= duration:
                        self.hits.popleft()
                    hits = tuple(self.hits)
                colors = render_frame(self.profile,hits,now) if hits else base
                if colors != previous:
                    changed = True
                    if not write_frame(self.reader,colors,previous,self.stopped):
                        break
                    previous = colors
        except Exception:
            self.status = 'Keypress effect stopped: reconnect in Cable mode and apply the profile again.'
        finally:
            self.stopped.set()
            if changed:
                try:
                    write_frame(self.reader,base)
                except Exception:
                    pass
            if self.listener:
                self.listener.stop()
