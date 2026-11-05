#!/usr/bin/env python3
"""Reject incomplete or reset native windows rather than inferring FPS."""
import unittest
from native_rate import interval


class NativeRateTests(unittest.TestCase):
    def test_exact_window_and_field_wrap(self):
        events = [dict(frame=150+i,field=(0xfffffffa+12*i)&0xffffffff) for i in range(4)]
        result = interval(events,150,153,60)
        self.assertEqual(result['presentations'],3)
        self.assertEqual(result['fields'],36)
        self.assertEqual(result['presentations_hz'],5)
        self.assertEqual(result['largest_presentation_gap_fields'],12)

    def test_missing_or_repeated_frame(self):
        for frames in ([150,152],[150,151,151,152],[150,151],[150,151,0,152]):
            with self.subTest(frames=frames), self.assertRaises(ValueError):
                interval([dict(frame=f,field=10*i) for i,f in enumerate(frames)],150,152,60)

    def test_backwards_or_stopped_field_clock(self):
        for fields in ([10,9,30],[10,10,10]):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                interval([dict(frame=150+i,field=f) for i,f in enumerate(fields)],150,152,60)

    def test_reject_bad_frequency_or_bounds(self):
        for start,end,hz in ((150,150,60),(150,152,59),(0,65536,60)):
            with self.subTest(start=start,end=end,hz=hz), self.assertRaises(ValueError):
                interval([],start,end,hz)


if __name__ == '__main__':
    unittest.main()
