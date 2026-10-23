#!/usr/bin/env python3
"""Executable C1 design, not an installed game patch. No game inputs required."""
import random
import unittest

MASK = (1 << 32) - 1


class Clock:
    def __init__(self, rate, serial=0):
        if rate not in (50, 60):
            raise ValueError('unsupported field rate')
        self.rate = rate
        self.intervals = (7, 6, 6, 6) if rate == 50 else (8, 7)
        self.rebase(serial)

    def rebase(self, serial):
        self.last = serial & MASK
        self.credit = self.phase = 0
        self.observed = self.consumed = self.dropped = self.ticks = 0

    def observe(self, serial):
        now = serial & MASK
        elapsed = (now - self.last) & MASK
        self.last = now
        self.observed += elapsed
        # Compare before adding in the eventual 32-bit implementation.
        accepted = min(elapsed, self.rate - self.credit)
        self.credit += accepted
        self.dropped += elapsed - accepted

    def batch(self):
        count = 0
        while count < 4:
            interval = self.intervals[self.phase]
            if self.credit < interval:
                break
            self.credit -= interval
            self.consumed += interval
            self.phase = (self.phase + 1) % len(self.intervals)
            self.ticks += 1
            count += 1
        return count


class ClockDesignTests(unittest.TestCase):
    def check_accounting(self, clock):
        self.assertEqual(clock.observed,
                         clock.consumed + clock.credit + clock.dropped)
        self.assertLessEqual(clock.credit, clock.rate)
        self.assertGreaterEqual(clock.credit, 0)

    def test_each_field_against_independent_due_tick_formula(self):
        for rate in (50, 60):
            clock = Clock(rate)
            for field in range(1, 100 * rate + 1):
                clock.observe(field)
                clock.batch()
                self.assertEqual(clock.ticks, field * 8 // rate)
                self.check_accounting(clock)
            self.assertEqual(clock.dropped, 0)

    def test_irregular_observation_and_counter_wrap(self):
        for rate in (50, 60):
            rng = random.Random(1)
            epoch = MASK - 20
            clock = Clock(rate, epoch)
            elapsed = 0
            for _ in range(1000):
                elapsed += rng.randrange(0, 24)
                clock.observe(epoch + elapsed)
                while clock.batch():
                    self.check_accounting(clock)
                self.assertEqual(clock.ticks, elapsed * 8 // rate)
                self.assertEqual(clock.dropped, 0)
                self.check_accounting(clock)

    def test_cap_batches_and_no_double_count(self):
        for rate in (50, 60):
            clock = Clock(rate)
            clock.observe(10 * rate)
            self.assertEqual(clock.dropped, 9 * rate)
            self.assertEqual(clock.batch(), 4)
            clock.observe(10 * rate)
            self.assertEqual(clock.batch(), 4)
            self.assertEqual(clock.batch(), 0)
            self.assertEqual(clock.credit, 0)
            self.check_accounting(clock)

    def test_fields_during_work_and_partial_credit_at_cap(self):
        for rate in (50, 60):
            clock = Clock(rate)
            clock.observe(3)
            self.assertEqual(clock.batch(), 0)
            clock.observe(3 + rate)
            self.assertEqual(clock.dropped, 3)
            self.assertEqual(clock.batch(), 4)
            clock.observe(6 + rate)  # work consumed three more VBLs
            self.assertEqual(clock.batch(), 4)
            self.assertEqual(clock.credit, 3)
            self.check_accounting(clock)

    def test_rebase_does_not_replay_inactive_time(self):
        for rate in (50, 60):
            clock = Clock(rate)
            clock.observe(20)
            clock.batch()
            clock.rebase(10000)
            clock.observe(10000)
            self.assertEqual(clock.batch(), 0)
            clock.observe(10000 + rate)
            self.assertEqual(clock.batch(), 4)
            self.assertEqual(clock.batch(), 4)
            self.check_accounting(clock)


if __name__ == '__main__':
    unittest.main()
