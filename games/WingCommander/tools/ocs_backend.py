#!/usr/bin/env python3
"""Conservative C3 policy and bounded profile adapter; no clock inference."""
from ocs_reconstruct import ROOT

OPTIONS = {'auto': 0, 'native': 1, 'cpu': 2}
ARMS = ('native', 'fast-word', 'fast-long')


def choose(option, cpu, profile, ready):
    if ready != 7 or cpu not in (0, 10, 20, 30, 40, 60):
        return 0
    if option == 2:
        return 1 if cpu < 20 else 2
    return 2 if option == 0 and cpu == 20 and profile == 1 else 0


def source():
    return (ROOT/'whdload/ocs_backend.s').read_text()


def diagnostic(option, cpu, memory_base, source, size, profile='measured', unavailable=False):
    # Hardware bank bounds, not game offsets. MEMF_FAST also labels slow RAM.
    # Only the C2 fixture's owned reservation is admitted here. C4 must supply
    # equivalent proof from its real allocations before production integration.
    fast = memory_base == 0x200000 and 0x200000 <= source <= 0x600000-size
    ready = 7 if fast and size > 0 and not unavailable else 0
    cpu = int(cpu)-68000
    measured = int(profile == 'measured' and cpu == 20 and fast)
    inputs = (OPTIONS[option], cpu, measured, ready)
    selected = choose(*inputs)
    return dict(option=option, inputs=list(inputs), selected=selected,
                arm=ARMS[selected], profile='c2-pal-020-fast' if measured else 'unknown',
                unavailable=unavailable)
