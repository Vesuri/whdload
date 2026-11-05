"""Compile the shared WCFS recorder against a verified variant field clock.

The caller owns a disjoint Fast buffer (16+4*capacity bytes) and serialises calls.
No game hooks, allocations, IRQ publication or resload ABI are inferred here.
"""
from pathlib import Path
import re
from shared_cpu import preamble, select
from variants import get

ROOT = Path(__file__).resolve().parents[1]


def source(variant, capacity=2048):
    v = get(variant)
    if not 1 <= capacity <= 16384:
        raise ValueError('invalid recorder capacity')
    whole = (ROOT/'whdload/frame_stats.s').read_text()
    core = whole[whole.index('frame_stat:\n'):whole.index('frame_stats_flush:\n')]
    if (core.count('$7f02(a0)') != 2 or core.count('bne.s   .sample') != 2
            or core.count('move.w  26(sp),d2') != 1 or core.count('.done:\n') != 1):
        raise ValueError('shared recorder field operands changed')
    core = core.replace('$7f02(a0)', f'${v.A4_BASE+v.A4["field_clock"]:x}(a0)')
    # Bound a pathological torn/interrupting clock to four sample attempts.
    # Extra retry word is below the saved CCR, so update the event argument.
    core = core.replace('        move.w  ccr,-(sp)', '        move.w  ccr,-(sp)\n        move.w #3,-(sp)')
    core = core.replace('bne.s   .sample', 'bne.w   .retry')
    core = core.replace('move.w  26(sp),d2', 'move.w  28(sp),d2')
    core = core.replace('.done:\n', '''        bra.w .done
.retry:
        subq.w #1,(sp)
        bpl.w .sample
        lea frame_stats_dropped(pc),a0
        addq.l #1,(a0)
.done:
        addq.l #2,sp
''')
    core = re.sub(r'\b(b[a-z]+)\.s\b', r'\1.w', core)
    header = f'BUFFERED equ 0\nFS_RECORDS equ {capacity}\nFS_SKIP equ 0\n'
    wrappers = (ROOT/'whdload/recorder_window.s').read_text()
    return header+preamble(ROOT, v.CPU)+select(wrappers+core, v.CPU)
