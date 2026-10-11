"""Quick diagnostic: list HID interfaces, highlighting Keychron + raw HID."""
import hid

devs = hid.enumerate()
print(f"Totale interfacce HID: {len(devs)}\n")

print("--- Keychron (VID 0x3434) ---")
found = False
for d in devs:
    if d.get("vendor_id") == 0x3434:
        found = True
        up = d.get("usage_page") or 0
        u = d.get("usage") or 0
        raw = "  <-- RAW HID 0xFF60" if up == 0xFF60 else ""
        print(f"PID={d['product_id']:#06x} up={up:#06x} u={u:#04x} "
              f"path={d.get('path')!r} | {d.get('product_string')}{raw}")
if not found:
    print("(nessuna interfaccia con VID 0x3434)")

print("\n--- Qualsiasi device con 'keychron'/'k10' nel nome ---")
for d in devs:
    name = (d.get("product_string") or "")
    if "keychron" in name.lower() or "k10" in name.lower():
        print(f"VID={d['vendor_id']:#06x} PID={d['product_id']:#06x} "
              f"up={(d.get('usage_page') or 0):#06x} | {name}")
