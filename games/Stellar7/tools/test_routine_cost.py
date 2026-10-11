#!/usr/bin/env python3
"""Check call-edge and context boundaries in profiler cost attribution."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import routine_cost


def record(pc, cost, sp):
    return pc, cost, (0,)*15+(sp,0)


class Trace:
    fields = [0]

    def __init__(self, records):
        self.records = records

    def instructions(self, field):
        return iter(self.records)


class Costs(unittest.TestCase):
    def measure(self, records):
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'anchor.txt').write_text('code=0x100\nbase=0\n')
            with patch.object(routine_cost.barto, 'load', return_value=Trace(records)), patch.object(
                    routine_cost, 'contexts', return_value=[(0xf00, 0x1100), (0x8000, 0x9100)]):
                return routine_cost.measure(folder, 0)

    def test_call_and_interrupt_boundaries(self):
        result = self.measure([
            record(0x7fffffff, 11, 0x1000), record(0x100, 10, 0x1000),
            record(0x7fffffff, 3, 0xffc), record(0x102, 20, 0xffc),
            record(0x7fffffff, 5, 0x9000), record(0x800, 30, 0x9000),
            record(0x7fffffff, 7, 0xffc), record(0x104, 40, 0xffc),
            record(0x7fffffff, 4, 0x1004), record(0x200, 1, 0x1004),
        ])
        self.assertEqual(result['samples'], [70])
        self.assertEqual(result['same_context_gap_samples'], [3])
        self.assertEqual(result['mean_cycles_with_same_context_gaps'], 73)

    def test_mismatched_gap_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'snapshots differ'):
            self.measure([record(0x100, 10, 0x1000), record(0x7fffffff, 3, 0xffc),
                          record(0x102, 20, 0xffa)])

    def test_partial_call_is_excluded(self):
        result = self.measure([record(0x100, 10, 0x1000), record(0x200, 1, 0x1004),
                               record(0x100, 20, 0x1000)])
        self.assertEqual(result['samples'], [10])
        self.assertEqual(result['incomplete_at_end'], 1)


if __name__ == '__main__':
    unittest.main()
