"""Exact completed-control count for unpaused, single-epoch WORLD20 windows."""
import struct
from check_timing_capacity import check as check_capacity
from timing_report import input_state


def check_control_window(root, ticks, epoch):
    # Independently account for physical elapsed time, retained/assigned work,
    # every completed world step, and an unchanged session/discard ledger.
    check_capacity(root)
    first=input_state(root/'code.bin')
    last=input_state(root/'final-code.bin')
    assert not first['control_active'] and not last['control_active'], 'Incomplete boundary control'
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    chip=(root/'chip.bin').read_bytes()
    frame=struct.unpack_from('>I',chip,game+0xca46)[0]-base
    data=(root/'final-code.bin').read_bytes()
    world=data.find(b'PDW20T01',frame,frame+16384)
    assert world>=0
    end=struct.unpack_from('>I',data,world+12)[0]
    # The cursor points at the next movement. A control deadline is eligible
    # only at/before the final completed movement timestamp (cursor minus 4).
    expected=max(0,(end-4-first['clock'])//18+1)
    assert len(ticks)==expected, 'Control count differs from completed world-time coverage'
    assert ticks==[first['clock']-epoch+18*i for i in range(expected)], 'Missing or repeated control deadline'
    assert last['clock']==first['clock']+18*expected, 'Unobserved final control-clock mutation'
    return ticks[0],ticks[-1]
