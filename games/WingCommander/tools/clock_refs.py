#!/usr/bin/env python3
"""List static references to a data-hunk range from game code hunk 0.

Finds both forms the Aztec C executable uses: A4-relative small-data accesses
(A4 = data hunk 1 + 7ffe) in a linear disassembly, and absolute longwords
relocated to hunk 1. Prints one line per instruction: hunk 0 offset, access
form, data hunk offset and the disassembled instruction. Static only.

  python3 -I tools/clock_refs.py EXECUTABLE H0.dis LOW HIGH
"""
import bisect
import os
from pathlib import Path
import re
import struct
import sys

sys.path.insert(0, os.environ.get('AMIGA_PYLIB') or
                os.path.expanduser('~/.local/share/amiga/pylib'))
from amitools.binfmt.hunk import Hunk
from amitools.binfmt.hunk.HunkReader import HunkReader

SMALL_DATA_BASE = 0x7ffe
LOADED = (Hunk.HUNK_CODE, Hunk.HUNK_DATA, Hunk.HUNK_BSS)


def hunk0_relocs_to_data(path):
    reader = HunkReader()
    reader.read_file(path)
    index, code, relocs = -1, None, []
    for block in reader.hunks:
        if block['type'] in LOADED:
            index += 1
            if index == 0:
                code = block['data']
        elif block['type'] == Hunk.HUNK_ABSRELOC32 and index == 0:
            relocs.extend(block['reloc'].get(1, []))
    return code, relocs


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__.strip())
    exe, dis, low, high = sys.argv[1], sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16)
    pcs, text = [], []
    for line in Path(dis).read_text().splitlines():
        m = re.match(r'\s*([0-9a-f]+):\t[^\t]*\t(.*)', line)
        if m:
            pcs.append(int(m.group(1), 16))
            text.append(m.group(2))
    hits = {}
    for i, insn in enumerate(text):
        for m in re.finditer(r'(-?\d+)\(a4\)', insn):
            target = SMALL_DATA_BASE + int(m.group(1))
            if low <= target <= high:
                hits.setdefault(i, ('a4', target))
    code, relocs = hunk0_relocs_to_data(exe)
    for offset in relocs:
        target = struct.unpack('>I', code[offset:offset + 4])[0]
        if low <= target <= high:
            i = bisect.bisect_right(pcs, offset) - 1
            if i >= 0:
                hits.setdefault(i, ('abs', target))
    for i in sorted(hits):
        form, target = hits[i]
        print('%05x %-3s D:%04x %s' % (pcs[i], form, target, text[i]))


if __name__ == '__main__':
    main()
