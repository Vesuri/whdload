"""Load a profile_run.py capture: (Reduction, meta, label function)."""
import json
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev.callprofile import Reduction
def load(prof):
    p=Path(prof);red=Reduction.load(p/'profile.pkl.gz');meta=json.loads((p/'meta.json').read_text())
    RB,SL=meta['reloc_base'],meta['slave_at']
    def label(pc):
        if RB<=pc<RB+0x45800:return f'g:${pc-RB+0x1000:05x}'
        if SL<=pc<SL+0x1300:return f'slave:${pc-SL:04x}'
        if pc>=0xf80000:return f'rom:${pc:06x}'
        if pc<0x80000:return f'chip:${pc:05x}'
        return f'mem:${pc:06x}'
    return red,meta,label
