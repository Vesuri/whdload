"""Slave calls into relocated game code must target a chip entry jump.

M1, S3/F2 and F5 copy game code to fast RAM. Callers outside the copies reach it through
chip entry jumps or retargeted operands; a chip address without an entry still runs the
stale original, which under F5 reads the vacated render scratch.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parent.parent
DELTA = 0x3cb0
# M1's chip entries (Mercenary3.slave.asm, _hotentries) and its two blocks.
M1_ENTRIES = {0x4ede4, 0x4ee76, 0x4ee88, 0x5b030, 0x5b038, 0x5b050, 0x5b5c4}
M1_BLOCKS = [(0x4ede4, 0x4ef92), (0x5b030, 0x5b918)]


def table(text, label):
    """Rows of Disk.1 offsets (`$X-$3cb0`) in the dc.l table after LABEL."""
    rows = []
    for line in text.split('\n' + label + '\n', 1)[1].splitlines():
        if not line.strip().startswith('dc.l'):
            break
        values = [int(v, 16) for v in re.findall(r'\$([0-9a-f]+)-\$3cb0', line)]
        if not values:
            break
        rows.append(values)
    return rows


def unentered_calls():
    f2 = (ROOT / 'src/renderer-f2.i').read_text()
    f5 = (ROOT / 'src/translate-f5.i').read_text()
    moved = [tuple(r[:2]) for r in table(f2, '_f2_ranges') + table(f5, '_f5_blocks')]
    moved += M1_BLOCKS
    entries = {r[0] for r in table(f2, '_f2_entries') + table(f5, '_f5_entries')}
    entries |= M1_ENTRIES
    bad = []
    source = (ROOT / 'src/Mercenary3.slave.asm').read_text().splitlines()
    for number, line in enumerate(source, 1):
        match = re.search(r'\b(?:jsr|jmp)\s+\(\$([0-9a-f]+)\)\.l', line, re.I)
        if match:
            disk = int(match[1], 16) + DELTA
            if disk not in entries and any(a <= disk < b for a, b in moved):
                bad.append(f'line {number}: Disk.1 ${disk:X}')
    return moved, bad


class EntryCallTests(unittest.TestCase):
    def test_tables_parse(self):
        moved, _ = unentered_calls()
        self.assertGreater(len(moved), 30)

    def test_no_call_into_moved_code_without_entry(self):
        _, bad = unentered_calls()
        self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
