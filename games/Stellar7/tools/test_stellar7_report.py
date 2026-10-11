"""Focused regression checks for patched entries and interrupted call tracking."""
import unittest
from stellar7_report import analyse


class Trace:
    fields = [0]

    def __init__(self, entries):
        self.entries = entries

    def instructions(self, field):
        for pc, cost, sp in self.entries:
            registers = [0] * 16
            registers[15] = sp
            yield pc, cost, registers


class Memory:
    def word(self, pc):
        return {0x80: 0x4eb9, 0x110: 0x4ef9, 0x300: 0x4eb9}.get(pc, 0x4e71)

    def long(self, pc):
        assert pc == 0x112
        return 0x200


class Namer:
    starts = {0x100}

    def addr(self, pc):
        return f"fn:{pc:x}"


class AttributionTests(unittest.TestCase):
    def test_native_continuation_keeps_patched_entry_boundary(self):
        trace = Trace([(0x80, 2, 0x8000), (0x110, 3, 0x7ffc),
                       (0x200, 5, 0x7ffc), (0x118, 7, 0x7ffc),
                       (0x86, 2, 0x8000)])
        own, inclusive, calls, *_ = analyse(trace, Memory(), Namer(), trace.fields)
        self.assertEqual(own['fn:110'], 10)
        self.assertEqual(own['fn:100'], 0)
        self.assertEqual(inclusive['fn:200'], 15)
        self.assertEqual(calls['fn:200'], 1)
        self.assertEqual(sum(own.values()), 19)

    def test_interrupt_keeps_pending_calls_in_both_contexts(self):
        trace = Trace([(0x80, 2, 0x8000), (0x7fffffff, 1, 0x12000),
                       (0x300, 2, 0x11ffc), (0x400, 3, 0x11ff8),
                       (0x306, 2, 0x11ffc), (0x110, 3, 0x7ffc),
                       (0x200, 5, 0x7ffc), (0x118, 7, 0x7ffc),
                       (0x86, 2, 0x8000)])
        own, inclusive, calls, *_ = analyse(trace, Memory(), Namer(), trace.fields)
        self.assertEqual(calls['fn:200'], 1)
        self.assertEqual(calls['fn:400'], 1)
        self.assertEqual(inclusive['fn:200'], 15)
        self.assertEqual(inclusive['fn:400'], 3)
        self.assertEqual(sum(own.values()), 27)


if __name__ == '__main__':
    unittest.main()
