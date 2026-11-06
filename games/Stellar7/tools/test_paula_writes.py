#!/usr/bin/env python3
"""Check which custom-register writes the Paula oracle counts as audio."""
import unittest
import paula_writes


class AudioFilter(unittest.TestCase):
    def test_audio_registers(self):
        self.assertTrue(paula_writes.audio(0xa0, 0))
        self.assertTrue(paula_writes.audio(0xd8, 0x40))
        self.assertFalse(paula_writes.audio(0xe0, 0))   # bitplane pointer

    def test_dmacon_audio_bits_only(self):
        self.assertTrue(paula_writes.audio(0x96, 0x8000 | 0x0004))
        self.assertTrue(paula_writes.audio(0x96, 0x0001))
        self.assertFalse(paula_writes.audio(0x96, 0x8000))  # no channel bit
        self.assertFalse(paula_writes.audio(0x96, 0x8040))  # blitter

    def test_interrupt_audio_bits_only(self):
        self.assertTrue(paula_writes.audio(0x9a, 0x0080))
        self.assertTrue(paula_writes.audio(0x9c, 0x0400))
        self.assertFalse(paula_writes.audio(0x9c, 0x0040))  # BLIT
        self.assertFalse(paula_writes.audio(0x9a, 0x4000))  # INTEN


if __name__ == '__main__':
    unittest.main()
