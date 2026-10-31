#!/usr/bin/env python3
"""Executable C1/F3 design, not an installed game patch. No game inputs required."""
import random
import unittest

MASK = (1 << 32) - 1


STOCK = 0x2000
# F3: the stock 1/8 s, F1GP-Ed's frame rates (n x 1350 PAL, n x 1125 NTSC) and the
# slave's 20 Hz step.
STEPS = (STOCK, 2250, 2700, 3276, 3375, 4050, 4500, 5400, 5625, 6750)


def interval(quot, rem, phase):
    """world_clock_interval: whole fields from tick k's deadline to tick k+1's."""
    following = (phase + rem) & 0xffff
    return quot + (phase + rem > 0xffff) + (following != 0) - (phase != 0)


class Clock:
    def __init__(self, rate, serial=0, step=STOCK):
        if rate not in (50, 60):
            raise ValueError('unsupported field rate')
        self.rate = rate
        if not (step <= 0x7fff and step*rate >= 0x10000):
            step = STOCK
        self.step = step
        self.quot, self.rem = divmod(step*rate, 0x10000)
        self.limit = 0x8000 // step
        self.rebase(serial)

    def rebase(self, serial):
        self.last = serial & MASK
        self.credit = self.phase = 0
        self.observed = self.consumed = self.dropped = self.ticks = 0

    def due(self, fields):
        """Independent oracle: ticks whose deadline ceil(k x step x F / 65536) has passed."""
        return fields * 0x10000 // (self.step * self.rate)

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
        while count < self.limit:
            fields = interval(self.quot, self.rem, self.phase)
            if self.credit < fields:
                break
            self.credit -= fields
            self.consumed += fields
            self.phase = (self.phase + self.rem) & 0xffff
            self.ticks += 1
            count += 1
        return count


class ClockDesignTests(unittest.TestCase):
    def check_accounting(self, clock):
        self.assertEqual(clock.observed,
                         clock.consumed + clock.credit + clock.dropped)
        self.assertLessEqual(clock.credit, clock.rate)
        self.assertGreaterEqual(clock.credit, 0)

    def test_stock_schedule_is_c1s(self):
        for rate, table in ((50, (7, 6, 6, 6)), (60, (8, 7))):
            clock = Clock(rate)
            self.assertEqual(clock.limit, 4)
            seen = []
            for _ in range(2 * len(table)):
                seen.append(interval(clock.quot, clock.rem, clock.phase))
                clock.phase = (clock.phase + clock.rem) & 0xffff
            self.assertEqual(tuple(seen), table * 2)

    def test_each_field_against_independent_due_tick_formula(self):
        for step in STEPS:
            for rate in (50, 60):
                clock = Clock(rate, step=step)
                for field in range(1, 100 * rate + 1):
                    clock.observe(field)
                    clock.batch()
                    self.assertEqual(clock.ticks, clock.due(field))
                    self.check_accounting(clock)
                self.assertEqual(clock.dropped, 0)
                # 65536/step ticks a second, whatever the display.
                self.assertEqual(clock.ticks, 100 * 0x10000 // step)

    def test_irregular_observation_and_counter_wrap(self):
        for step in STEPS:
            for rate in (50, 60):
                rng = random.Random(1)
                epoch = MASK - 20
                clock = Clock(rate, epoch, step)
                elapsed = 0
                for _ in range(1000):
                    elapsed += rng.randrange(0, 24)
                    clock.observe(epoch + elapsed)
                    while clock.batch():
                        self.check_accounting(clock)
                    self.assertEqual(clock.ticks, clock.due(elapsed))
                    self.assertEqual(clock.dropped, 0)
                    self.check_accounting(clock)

    def test_cap_batches_and_no_double_count(self):
        for step in STEPS:
            for rate in (50, 60):
                clock = Clock(rate, step=step)
                clock.observe(10 * rate)
                self.assertEqual(clock.dropped, 9 * rate)
                self.assertEqual(clock.batch(), min(clock.limit, clock.due(rate)))
                while clock.batch():
                    pass
                self.assertEqual(clock.ticks, clock.due(rate))
                self.check_accounting(clock)

    def test_batch_is_half_a_second_of_steps(self):
        for step in STEPS:
            clock = Clock(50, step=step)
            self.assertEqual(clock.limit, 0x8000 // step)
            self.assertGreaterEqual(clock.limit, 1)
        self.assertEqual(Clock(50, step=3276).limit, 10)

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

    def test_invalid_steps_keep_the_stock_schedule(self):
        for step in (0, 1, 1310, 0x8000, 0xffff):
            self.assertEqual(Clock(50, step=step).step, STOCK)
        self.assertEqual(Clock(50, step=1311).step, 1311)
        self.assertEqual(Clock(60, step=1093).step, 1093)


if __name__ == '__main__':
    unittest.main()
