"""Where the game runs: with fast ExpMem the slave copies $1000-$687ff there (docs/internals.md,
"CPU-only data in fast memory"), so every address in it but the chip data moves by one
distance. The game writes its level 3 vector as `move.l #$60740,$6c`; chip $6c then holds
$60740 plus that distance (0 without fast ExpMem; ExpMem and $1000 are both 4 KB aligned).
"""
CODE = (0x57000, 0x68800)
MOVED = (0x1000, 0x68800)
CHIP = (0x3ca1e, 0x4a546)    # the copper lists and the samples stay
LEVEL3 = 0x60740


def peek(srv, addr, n, tries=3):
    """N bytes at ADDR as a number; retries a reply without them (the stub now and then
    answers a peek with a gdb message)."""
    for _ in range(tries):
        try:
            txt = srv.request(f'peek {addr:x} {n}')
        except Exception as e:  # noqa: BLE001 - the server reports a stub message as an error
            txt = str(e)
            continue
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
        if v == LEVEL3 or (v - LEVEL3) & 0xfff == 0 and 0x200000 <= v < 0xf80000:
            return v - LEVEL3
        srv.request('fields 10')
    raise RuntimeError('the game has not set its level 3 vector')


def moves(addr):
    return MOVED[0] <= addr < MOVED[1] and not CHIP[0] <= addr < CHIP[1]


def at(addr, d):
    """A game address where it is."""
    return addr + d if moves(addr) else addr
