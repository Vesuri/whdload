"""Check _handling_turn (HardDrivinHandling.s) in Unicorn against a Python model.

check_handling_turn.py SLAVE LISTING RUN [--cases N] [--seed S]   (from tools)

RUN is any capture directory with game-code.bin and game-data.bin
(capture_feel.py output): the check runs the game's own sine
and cosine ($2AC4/$2ACA) and sine table (G($833C)) from it, at the a4 jump
table entries the module calls. The module's far pointers are aimed at a
fake _motion_state, a fields word and a stub for _motion_yaw_rate that logs
its argument and the fields word it saw.

Each case sets heading, pitch and roll (within and beyond +-720), the three
enhanced "last angle" words, D0 = the turn and D6/D7/A2-A6 to markers, calls
_handling_turn and compares: upright (|pitch| and |roll| below 240 after
wrapping) adds the turn to the heading and rotates (pitch, roll) by it, each
rounded, with the same changes in the last-angle words; otherwise the stub
gets the turn with fields 8, and fields is restored. D6/D7/A2-A6 and the
stack must be preserved.
"""
import argparse
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_handling_step import C, ok, u, code_hunk, label_offsets   # noqa: E402

# unicorn m68k register numbers: A0..A7 = 1..8, D0..D7 = 9..16
UC_A0, UC_D0 = 1, 9

BASE, A4, SINE, MOTION, FIELDS, STUB, LOG, STACK, END = (
    0x10000, 0x90000, 0xa0000, 0xa1000, 0xa1100, 0xa1200, 0xa1300, 0xafff0, 0xa2000)
MS_YAW, MS_PITCH, MS_ROLL = 0, 6, 12


def g(x):
    return A4 + x - 0x10000


class Emu:
    def __init__(self, code, off, game_code, game_data):
        self.h = C.c_void_p()
        ok(u.uc_open(7, 1 << 30, C.byref(self.h)))
        ok(u.uc_ctl(self.h, 0x44000007, C.c_int(1)))
        ok(u.uc_mem_map(self.h, 0, 0x100000, 7))
        self.write(BASE, code)
        # the game's cosine (falls into the sine) and the sine table
        cos = 0x2ac4
        self.write(SINE, game_code[cos:cos + 0x4a])
        tab = 0x833c - 0x10000 + 0x7ffe            # G($833C) in the data hunk (a4 = base + $7FFE)
        self.write(g(0x833c), game_data[tab:tab + 722])
        self.table = struct.unpack('>361h', game_data[tab:tab + 722])
        self.write(g(0x80d4), struct.pack('>HI', 0x4ef9, SINE))          # cosine
        self.write(g(0x80da), struct.pack('>HI', 0x4ef9, SINE + 6))      # sine
        # _motion_yaw_rate stub: log the argument and fields, pop the argument
        stub = bytes.fromhex('33ef0004') + struct.pack('>I', LOG) + \
            bytes.fromhex('33f9') + struct.pack('>II', FIELDS, LOG + 2) + \
            bytes.fromhex('52b9') + struct.pack('>I', LOG + 4) + \
            bytes.fromhex('2f5700024a5f4e75')
        # move.w 4(a7),LOG; move.w FIELDS,LOG+2; addq.l #1,LOG+4;
        # move.l (a7),2(a7); tst.w (a7)+; rts
        self.write(STUB, stub)
        for name, value in (('_handling_motion', MOTION), ('_handling_fields', FIELDS),
                            ('_handling_yaw_rate', STUB)):
            self.write(BASE + off[name], struct.pack('>I', value))
        self.turn = BASE + off['_handling_turn']
        self.write(END, bytes.fromhex('4e714e71'))

    def write(self, a, b):
        ok(u.uc_mem_write(self.h, a, b, len(b)))

    def read(self, a, n):
        b = C.create_string_buffer(n)
        ok(u.uc_mem_read(self.h, a, b, n))
        return b.raw

    def reg(self, k, v=None):
        x = C.c_uint32(0 if v is None else v & 0xffffffff)
        if v is None:
            ok(u.uc_reg_read(self.h, k, C.byref(x)))
            return x.value
        ok(u.uc_reg_write(self.h, k, C.byref(x)))

    def gsin(self, a):
        """The game's sine, as $2ACA computes it."""
        neg = a < 0
        d = -a if neg else a
        if d >= 1440:
            d %= 1440
        if d > 720:
            neg, d = not neg, d - 720
        if d > 360:
            d = 720 - d
        v = self.table[d]
        return -v if neg else v


def wrap(a):
    if a > 720:
        a -= 1440
    if a < -720:
        a += 1440
    return a


def w16(x):
    return (x + 32768) % 65536 - 32768


def run_case(e, rnd, big):
    head, pitch, roll = (rnd.randint(-1440, 1440) for _ in range(3))
    if rnd.random() < 0.6:          # mostly upright
        pitch, roll = rnd.randint(-300, 300), rnd.randint(-300, 300)
    turn = rnd.randint(-720, 720) if big else rnd.choice([-1, 1]) * rnd.randint(1, 60)
    last = [rnd.randint(-2000, 2000) for _ in range(3)]
    fields = rnd.randint(1, 50)
    e.write(g(0x994a), struct.pack('>hhh', head, pitch, roll))
    for k, o in enumerate((MS_YAW, MS_PITCH, MS_ROLL)):
        e.write(MOTION + o, struct.pack('>ih', 0x12345678, last[k]))
    e.write(FIELDS, struct.pack('>h', fields))
    e.write(LOG, bytes(8))
    e.write(STACK, struct.pack('>I', END))
    marks = {6: 0x66666666, 7: 0x77777777}
    for k, v in marks.items():
        e.reg(UC_D0 + k, v)
    for k in range(2, 7):
        e.reg(UC_A0 + k, 0xa0a0a000 + k if k != 4 else A4)
    e.reg(UC_D0, turn & 0xffff)
    e.reg(UC_A0 + 7, STACK)
    ok(u.uc_emu_start(e.h, e.turn, END, 0, 100000))
    # preserved registers and stack
    for k, v in marks.items():
        assert e.reg(UC_D0 + k) == v, 'D%d' % k
    for k in range(2, 7):
        assert e.reg(UC_A0 + k) == (0xa0a0a000 + k if k != 4 else A4), 'A%d' % k
    assert e.reg(UC_A0 + 7) == STACK + 4
    got = struct.unpack('>hhh', e.read(g(0x994a), 6))
    got_last = [struct.unpack('>ih', e.read(MOTION + o, 6)) for o in (MS_YAW, MS_PITCH, MS_ROLL)]
    log_turn, log_fields, log_calls = struct.unpack('>hhI', e.read(LOG, 8))
    got_fields = struct.unpack('>h', e.read(FIELDS, 2))[0]
    p, r = wrap(pitch), wrap(roll)
    case = (head, pitch, roll, turn)
    assert got_fields == fields, case
    assert all(c == 0x12345678 for c, _ in got_last), case
    if abs(p) >= 240 or abs(r) >= 240:
        assert log_calls == 1 and log_turn == turn and log_fields == 8, case
        assert got == (head, pitch, roll), case
        assert [x for _, x in got_last] == last, case
        return 'native'
    assert log_calls == 0, case
    s, c = e.gsin(turn), e.gsin(w16(turn + 360))
    p2 = (p * c - r * s + 8192) >> 14
    r2 = (p * s + r * c + 8192) >> 14
    want = (w16(head + turn), w16(pitch + p2 - p), w16(roll + r2 - r))
    assert got == want, (case, got, want)
    assert [x for _, x in got_last] == [w16(last[0] + turn), w16(last[1] + p2 - p), w16(last[2] + r2 - r)], case
    return 'upright'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('slave')
    ap.add_argument('listing')
    ap.add_argument('run')
    ap.add_argument('--cases', type=int, default=200000)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    code = code_hunk(a.slave)
    off = label_offsets(a.listing, ['_handling_turn', '_handling_motion', '_handling_fields', '_handling_yaw_rate'])
    run = Path(a.run)
    e = Emu(code, off, (run / 'game-code.bin').read_bytes(), (run / 'game-data.bin').read_bytes())
    rnd = random.Random(a.seed)
    count = {'upright': 0, 'native': 0}
    for i in range(a.cases):
        count[run_case(e, rnd, i % 10 == 0)] += 1
    print('%d cases: %d upright (rotated), %d native; all equal the model' % (a.cases, count['upright'], count['native']))


if __name__ == '__main__':
    main()
