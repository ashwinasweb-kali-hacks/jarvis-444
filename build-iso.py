#!/usr/bin/env python3
"""Build jarvis-hologram.iso from iso-staging/ using pycdlib."""
import io, re
from pathlib import Path
import pycdlib

STAGING = Path(__file__).resolve().parent / "iso-staging"
OUT = Path(__file__).resolve().parent / "jarvis-hologram.iso"

def iso_name(name: str, is_dir: bool = False) -> str:
    # ISO9660 d1 chars: A-Z, 0-9, _. Level 2 allows up to 31 chars.
    # Directory identifiers cannot contain dots.
    if is_dir:
        s = re.sub(r"[^A-Za-z0-9_]", "_", name).upper()
    else:
        # keep a single dot separator for extension
        base, ext = os.path.splitext(name)
        base = re.sub(r"[^A-Za-z0-9_]", "_", base).upper()
        ext = re.sub(r"[^A-Za-z0-9]", "", ext).upper()
        if ext:
            s = base + "." + ext
        else:
            s = base
    if len(s) > 31:
        s = s[:31]
    return s

import os

iso = pycdlib.PyCdlib()
iso.new(interchange_level=2, joliet=3, rock_ridge="1.09", vol_ident="JARVIS_HOLOGRAM")

def walk(local_dir: Path, iso_dir: str, joliet_dir: str, rr_dir: str):
    for entry in sorted(local_dir.iterdir()):
        name_iso = iso_name(entry.name, is_dir=entry.is_dir())
        child_iso = iso_dir.rstrip("/") + "/" + name_iso
        child_joliet = joliet_dir.rstrip("/") + "/" + entry.name
        child_rr = rr_dir.rstrip("/") + "/" + entry.name
        if entry.is_dir():
            try:
                iso.add_directory(iso_path=child_iso, rr_name=entry.name, joliet_path=child_joliet)
            except Exception as e:
                print("dir err", child_iso, e)
            walk(entry, child_iso, child_joliet, child_rr)
        else:
            with open(entry, "rb") as f:
                data = f.read()
            iso.add_fp(io.BytesIO(data), len(data), iso_path=child_iso, rr_name=entry.name, joliet_path=child_joliet)

for entry in sorted(STAGING.iterdir()):
    name_iso = iso_name(entry.name, is_dir=entry.is_dir())
    child_iso = "/" + name_iso
    child_joliet = "/" + entry.name
    if entry.is_dir():
        try:
            iso.add_directory(iso_path=child_iso, rr_name=entry.name, joliet_path=child_joliet)
        except Exception as e:
            print("dir err", child_iso, e)
        walk(entry, child_iso, child_joliet, child_iso)
    else:
        with open(entry, "rb") as f:
            data = f.read()
        iso.add_fp(io.BytesIO(data), len(data), iso_path=child_iso, rr_name=entry.name, joliet_path=child_joliet)

iso.write(str(OUT))
iso.close()
print("Wrote", OUT, OUT.stat().st_size, "bytes")
