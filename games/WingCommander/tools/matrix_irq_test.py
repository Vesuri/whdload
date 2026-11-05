#!/usr/bin/env python3
"""Synthetic scope accounting checks; no game data or emulator required."""
import unittest
from matrix_irq_check import integrate


class ScopeAccounting(unittest.TestCase):
    cuts = [(0, 0), (1, 7), (2, 10)]
    lines = ['B 0 0', 'E 1 0 2 334162 4000 5000',
             'E 2 1 4 327810 3ff0 5100', 'R 2 6 5100 3ff4',
             'B 1 7', 'R 1 9 5000 4004', 'B 2 10']

    def test_nested_callback_across_scene(self):
        rows = integrate(self.lines, self.cuts, 0x300000)
        self.assertEqual(rows[0]['inclusive_units'], [5, 2, 0])
        self.assertEqual(rows[1]['inclusive_units'], [2, 0, 0])
        self.assertEqual(rows[0]['callback_union_units'], 5)
        self.assertEqual(rows[0]['innermost_selected_callback_units'], [3, 2, 0])
        self.assertEqual(rows[1]['entries'], [0, 0, 0])
        self.assertEqual(rows[1]['returns'], [1, 0, 0])

    def test_reject_corruptions(self):
        for before, after in [
            ('R 2 6 5100 3ff4', 'R 1 6 5100 3ff4'),
            ('R 1 9 5000 4004', 'R 1 9 5000 4000'),
            ('B 1 7', 'B 1 8'),
            ('R 1 9 5000 4004', 'R 1 5 5000 4004'),
            ('E 2 1 4', 'E 3 1 4'),
            ('334162', '334164'),
        ]:
            with self.subTest(after=after), self.assertRaises(ValueError):
                integrate([line.replace(before, after) for line in self.lines], self.cuts, 0x300000)
        with self.assertRaises(ValueError):
            integrate(self.lines[:-1], self.cuts, 0x300000)
        with self.assertRaises(ValueError):
            integrate([line for line in self.lines if not line.startswith('R 1 ')], self.cuts, 0x300000)


if __name__ == '__main__':
    unittest.main()
