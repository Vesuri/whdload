"""Shared assertions against a native constructor's muzzle and movement step."""


def check_path(muzzle, velocity, advance, snapshot, rate, debt, begin, end, state):
    # The caller has executed one native movement step. Test the whole path,
    # not just its first sample: no hold, accelerated catch-up or tick jump.
    tick = 0
    count = 0
    for hz in (50, 60):
        rate(hz)
        for _ in range(3):
            before = state()
            samples = []
            # Display fraction = debt + one lead field (10 units at 10 Hz);
            # the bolt shows it two fields late, up to the predictor's bound
            # of one tick plus two fields (the completed endpoint).
            for fraction in range(10, hz + 21, 10):
                debt(fraction - 10)
                got = begin()
                for actual, origin, speed in zip(got, muzzle, velocity):
                    numerator = speed * (tick * hz + fraction - 20)
                    displacement = abs(numerator) // hz * (-1 if numerator < 0 else 1)
                    assert abs(actual - origin - displacement) <= 1, (
                        'muzzle trajectory', tick, hz, fraction, got, muzzle, velocity)
                samples.append(got)
                end()
                assert state() == before, 'projectile presentation changed game state'
                count += 1
            if any(abs(v) > hz for v in velocity):
                assert len(set(samples[:hz // 10])) == hz // 10, 'projectile held'
            endpoint = tuple(m + v * (tick + 1) for m, v in zip(muzzle, velocity))
            assert samples[-1] == endpoint, 'bound sample is not the completed endpoint'
            advance()
            snapshot()
            tick += 1
    return count
