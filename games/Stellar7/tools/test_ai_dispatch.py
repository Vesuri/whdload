#!/usr/bin/env python3
"""Decision-gate encoding guards, independent of supplied game files."""
import unittest
from ai_dispatch import gate_sites


class GateEncodingTests(unittest.TestCase):
    def sample(self, branch):
        prefix = bytes.fromhex('4e71')*7
        gate = bytes.fromhex('426a00184a6a001a')+branch+bytes.fromhex('357c00010018')
        offsets = dict(s60_loop_step=len(prefix+gate), s60_last=100,
                       s60_logic=124, s60_phase=126)
        return prefix+gate, offsets

    def test_byte_and_word_branches(self):
        for encoded in ('6606', '66000008'):
            with self.subTest(encoded=encoded):
                body, offsets = self.sample(bytes.fromhex(encoded))
                self.assertEqual(gate_sites(body, offsets), (14, len(body)-6))

    def test_wrong_target_rejected(self):
        for encoded in ('6604', '66000006'):
            body, offsets = self.sample(bytes.fromhex(encoded))
            with self.assertRaisesRegex(AssertionError, 'unrecognized scheduler'):
                gate_sites(body, offsets)

    def test_wrong_phase_or_logic_rejected(self):
        for symbol in ('s60_phase', 's60_logic'):
            body, offsets = self.sample(bytes.fromhex('6606'))
            offsets[symbol] += 2
            with self.assertRaisesRegex(AssertionError, 'unrecognized scheduler'):
                gate_sites(body, offsets)

    def test_changed_gate_instruction_rejected(self):
        body, offsets = self.sample(bytes.fromhex('6606'))
        body = body[:14]+bytes.fromhex('4e71')+body[16:]
        with self.assertRaisesRegex(AssertionError, 'unrecognized scheduler'):
            gate_sites(body, offsets)


if __name__ == '__main__':
    unittest.main()
