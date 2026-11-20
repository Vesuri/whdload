"""Where the game's code runs: the slave copies the code area ($57000-$687ff) to ExpMem when
there is some (docs/internals.md, "Code in fast memory"), so every code address moves by
one distance. The game writes its level 3 vector as `move.l #$60740,$6c`; chip $6c then
holds $60740 plus that distance (0 without ExpMem; ExpMem and $57000 are both 4 KB aligned,
and ExpMem lies above the 544 KB BaseMem: in fast memory, or in chip memory on a machine
without any).
"""
CODE = (0x57000, 0x68800)
LEVEL3 = 0x60740


def peek(srv, addr, n, tries=3):
    """N bytes at ADDR as a number; retries a reply without them (the stub now and then
    answers a peek with a gdb message)."""
    for _ in range(tries):
        txt = srv.request(f'peek {addr:x} {n}')
        w = [w for w in txt.split() if len(w) == 2 * n]
        if w:
            try:
                return int(w[0], 16)
            except ValueError:
                pass
    raise RuntimeError(f'peek {addr:x} {n}: {txt.strip()}')


def delta(srv, tries=60):
    """The code's distance from $57000, running 10 fields at a time until the game has set
    its level 3 vector (from a fresh boot, before the demo starts)."""
    for _ in range(tries):
        v = peek(srv, 0x6c, 4)
        if v == LEVEL3 or (v - LEVEL3) & 0xfff == 0 and 0x88000 <= v < 0xf80000:
            return v - LEVEL3
        srv.request('fields 10')
    raise RuntimeError('the game has not set its level 3 vector')


def at(addr, d):
    """A code-area address where it runs."""
    return addr + d if CODE[0] <= addr < CODE[1] else addr
