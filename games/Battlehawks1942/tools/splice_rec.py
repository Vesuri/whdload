#!/usr/bin/env python3
"""Splice synthetic input events into an idle FS-UAE input recording.

  python3 tools/splice_rec.py BASE.rec OUT.rec FRAME:EVENT[:HOLD] ...

Each FRAME:EVENT presses input event EVENT at the start of emulated frame FRAME (line 1) and
releases it HOLD frames later (default 5). BASE.rec is a recording made with no input
(`RECORD=... amiga/run.sh` in warp, ended with SIGTERM) that runs past the last release.

FS-UAE recording format (big-endian uint32): per frame `0x80000000|frame`,
`0x10000000|rand checksum`, `0x08000000|state checksum`; then that frame's events as
`0x40000000|line`, `0x20000000|state<<16|event`. Playback invalidates the recording on a rand
checksum mismatch but only notifies on a state checksum mismatch, so the idle baseline's
later state checksums may differ from the spliced run without stopping playback.
Event numbers are this FS-UAE binary's (docs/profiling.md): KEY_RETURN = 164.
"""
import struct, sys

KEY_RETURN = 164


def main():
    base, out, specs = sys.argv[1], sys.argv[2], sys.argv[3:]
    d = open(base, 'rb').read()
    words = list(struct.unpack(f'>{len(d) // 4}I', d))
    events = {}
    for s in specs:
        parts = [int(x, 0) for x in s.split(':')]
        frame, event, hold = (parts + [5])[:3]
        events.setdefault(frame, []).append((1, event))
        events.setdefault(frame + hold, []).append((0, event))
    res, frames = [], set()
    i = 0
    while i < len(words):
        w = words[i]
        res.append(w)
        if w & 0x80000000:
            frame = w & 0x7fffffff
            frames.add(frame)
            res.extend(words[i + 1:i + 3])  # rand and state checksums
            i += 3
            for state, event in events.get(frame, []):
                res += [0x40000001, 0x20000000 | state << 16 | event]
            continue
        i += 1
    missing = sorted(set(events) - frames)
    if missing:
        sys.exit(f'baseline ends before frames {missing}; record a longer one')
    open(out, 'wb').write(struct.pack(f'>{len(res)}I', *res))
    print(f'{out}: {len(res)} words, events at {sorted(events)}')


if __name__ == '__main__':
    main()
