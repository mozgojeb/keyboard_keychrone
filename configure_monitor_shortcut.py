"""Configure the user's requested Ctrl+Insert toggle without changing input."""
from datetime import datetime
import json
from pathlib import Path
import os
import shutil
import argparse
from keeb_assistant.monitor_control import MonitorControl
from keeb_assistant.monitor_shortcuts import MonitorShortcuts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--shortcut',default='Ctrl+Insert')
    parser.add_argument('--disabled',action='store_true')
    args = parser.parse_args()
    monitors = [m for m in MonitorControl().discover() if 'MSI3DD2' in m['id']]
    if len(monitors)!=1 or not {15,16}.issubset(monitors[0]['inputs']):
        raise RuntimeError('The expected MSI monitor and input codes were not found.')
    monitor = monitors[0]
    settings = dict(enabled=not args.disabled,monitor_id=monitor['id'],first=16,second=15,shortcut=args.shortcut)
    # Registration is checked without issuing any monitor command.
    service = MonitorShortcuts()
    try:
        service.configure(settings)
    finally:
        service.stop()
    path = Path(os.environ['APPDATA'])/'KeyboardCompanion'/'config.json'
    source = json.loads(path.read_text(encoding='utf-8-sig'))
    backup = path.with_name('config.before-monitor-shortcut-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    shutil.copy2(path,backup)
    source['monitor_shortcut'] = settings
    temporary = path.with_suffix('.monitor.tmp')
    temporary.write_text(json.dumps(source,indent=2),encoding='utf-8')
    os.replace(temporary,path)
    print(f"Configured {monitor['name']}: {args.shortcut}, enabled={not args.disabled}, USB-C (0x10) / DP (0x0F).")
    print(f"Current input reading: {monitor['current']}. No source-change commands sent.")


if __name__=='__main__': main()
