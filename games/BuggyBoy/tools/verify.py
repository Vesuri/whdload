#!/usr/bin/env python3
"""Read the VERIFY build's log of frames drawn between ticks (src/Enhanced.s, _Verify).

    python3 tools/verify.py        on a running server of a VERIFY build

Each frame between ticks saves the state, draws and restores it; the VERIFY build then
compares the whole program and COURSES.DAT with copies from before the frame, but for what the level-3
handler writes. Prints the frames checked and every program offset that differed; then the frames whose
road, drawn in fast memory, was compared with the original's drawn in chip, and the
longwords that differed; then the same for the clear's rows 0 to 103, queued to the blitter,
against the original clear drawn after it (and the frames whose horizon step differed).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import route  # noqa: E402

LOG_POINTER = 0x3C0


def read():
    log = route.peek(LOG_POINTER)
    frames, diffs = route.peek(log), route.peek(log + 4)
    entries = []
    for i in range(200):
        w = route.peek(log + 8 + 4 * i)
        if not w:
            break
        entries.append((w >> 16, w & 0xFFFF))
    return (frames, diffs, entries, route.peek(log + 0x340), route.peek(log + 0x344),
            route.peek(log + 0x348), route.peek(log + 0x34C))


if __name__ == '__main__':
    frames, diffs, entries, roads, road_diffs, clears, clear_diffs = read()
    print(f'frames between ticks checked {frames}, differing longwords {diffs}')
    print(f'roads drawn in fast memory checked {roads}, differing longwords {road_diffs}')
    print(f'clears queued checked {clears & 0xFFFF}, differing longwords {clear_diffs}, '
          f'horizon differing {clears >> 16}')
    for off, n in entries:
        if off & 0x8000:
            print(f'  COURSES.DAT +{(off & 0x7fff) * 2:05x}  x{n}')
        else:
            print(f'  +{off:05x}  x{n}')
