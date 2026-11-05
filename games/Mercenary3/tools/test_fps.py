"""Offline checks for the frame counter's boundaries, stamps and failure handling."""
import signal
import time
import unittest
from unittest.mock import Mock

from fps import at_breakpoint, deadline, delta, publication_intervals, require_pal, word


class FrameCounterTests(unittest.TestCase):
    def test_rejects_ntsc_or_unknown_timing(self):
        require_pal({'ntsc': 'false'})
        for settings in ({'ntsc': 'true'}, {}):
            with self.assertRaises(RuntimeError):
                require_pal(settings)

    def test_counter_wrap(self):
        self.assertEqual(delta(2, 65534), 4)

    def test_reads_fail_closed(self):
        g = Mock()
        g.cmd.return_value = '0x7180:\t0x0059'
        self.assertEqual(word(g, 0x7180), 89)
        g.cmd.return_value = '0x7180: Cannot access memory'
        with self.assertRaises(RuntimeError):
            word(g, 0x7180)

    def test_continue_must_reach_expected_breakpoint(self):
        g = Mock()
        g.cmd.side_effect = ['Program received signal SIGINT', 'pc 0x4b100']
        with self.assertRaises(RuntimeError):
            at_breakpoint(g, 0x4b100, 1)
        g.cmd.side_effect = ['Breakpoint 1', 'pc 0x4b102']
        with self.assertRaises(RuntimeError):
            at_breakpoint(g, 0x4b100, 1)

    def test_stamp_is_from_previous_publication(self):
        # At publication i, dt/stamp still describe i-1. Exclude the startup stamp.
        samples = [dict(frames=65534, stamp=65520, dt=2),
                   dict(frames=65535, stamp=65526, dt=6),
                   dict(frames=0, stamp=65533, dt=7),
                   dict(frames=1, stamp=3, dt=6)]
        self.assertEqual(publication_intervals(samples),
                         [dict(frame=65535, fields=7), dict(frame=0, fields=6)])
        samples[-1]['dt'] = 5
        with self.assertRaises(RuntimeError):
            publication_intervals(samples)
        samples[-1].update(dt=6, frames=2)
        with self.assertRaises(RuntimeError):
            publication_intervals(samples)

    def test_deadline_interrupts_and_restores_handler(self):
        before = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(TimeoutError, 'test boot exceeded'):
            with deadline(0.02, 'test boot'):
                time.sleep(1)
        self.assertEqual(signal.getsignal(signal.SIGALRM), before)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))


if __name__ == '__main__':
    unittest.main()
