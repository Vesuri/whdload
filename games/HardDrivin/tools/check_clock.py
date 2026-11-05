"""Check HardDrivinClock.s (arcade race timing, CUSTOM5=1) against a Python model.

check_clock.py SLAVE LISTING [--fields N] [--seed S]

Loads the slave's code hunk into Unicorn (68000 model) with the game globals
at a private A4 and calls the module's routines directly:
- the BCD helpers on every clock value up to 10 minutes (add and subtract 0..9
  hundredths) and the binary conversions on every value up to 99:59.99;
- the VBL routine over random race sequences (before the start, running,
  crash, instant replay with the gate closed, pause, Phantom race, time out,
  an award in progress), comparing both clocks, the time-out flag and the
  module state after every field;
- the checkpoint and finish awards, race set-up, both starts, the off-road
  deadline and its time left, the time-out test and the Phantom champion's
  lap over random states.
Exits nonzero on the first difference. The limits are _clock_limits as stored,
the arcade's own (the installer, not run here, doubles them unless CUSTOM1=2,
and for CUSTOM1=2 doubles the stop speed instead).
"""
import argparse
import random
import struct
import sys

from check_handling_step import C, I, P, code_hunk, label_offsets, ok, u

REG_A0, REG_A1, REG_A4, REG_A5, REG_A7, REG_D0, REG_D1 = 1, 2, 5, 6, 8, 9, 10
A4 = 0x70000
A5 = 0x8f000


def G(x):
    return A4 + x - 0x10000


LAP, QUAL, LEFT, OUT = G(0x9790), G(0x9794), G(0x9798), G(0x979c)
GATE, RACE, LEVEL, REPLAY, DEADLINE, STARTED = G(0x95ed), G(0xadd4), G(0xadd5), G(0xadd7), G(0xadd8), G(0xaddf)
CRASH, SPEED, STUNT, QUALIFIED, CHAMP, PHANTOM = G(0x9606), G(0x9928), G(0x9950), G(0x9c9e), G(0xaf00), G(0xe931)
CS = dict(fraction=(0, 'I'), overtime=(4, 'I'), champion=(8, 'I'), native_lap=(12, 'I'), native_left=(16, 'I'),
          crash=(20, 'H'), handicap=(22, 'H'), finishes=(24, 'H'), pending=(26, 'H'), expired=(28, 'B'),
          busy=(29, 'B'), played=(30, 'B'), qualified=(31, 'B'))
PRESETS = [(9600, 4800, 4700, 4600), (9000, 4400, 4400, 4500), (8400, 4300, 4300, 4400)]
ROUTINES = ['_clock_vbl', '_clock_bcd_add', '_clock_bcd_sub', '_clock_from_bcd', '_clock_to_bcd', '_clock_state',
            '_clock_checkpoint', '_clock_finish', '_clock_race_init', '_clock_auto_start', '_clock_button_start',
            '_clock_offroad', '_clock_offroad_left', '_clock_expired', '_clock_champion']


def bcd(v):
    return (v // 10) << 4 | v % 10


def unbcd(b):
    return (b >> 4) * 10 + (b & 15)


def to_bcd(h):
    m, r = divmod(h, 6000)
    return bcd(m) << 16 | bcd(r // 100) << 8 | bcd(r % 100)


def from_bcd(v):
    return unbcd(v >> 16 & 255) * 6000 + unbcd(v >> 8 & 255) * 100 + unbcd(v & 255)


class Emu:
    BASE, STACK, END, STUB = 0x10000, 0x8fff0, 0x88000, 0x88010

    def __init__(self, code, off):
        self.h = P()
        ok(u.uc_open(7, 1 << 30, C.byref(self.h)))
        ok(u.uc_ctl(self.h, 0x44000007, I(1)))     # CPU model: 68000
        ok(u.uc_mem_map(self.h, 0, 0x100000, 7))
        self.write(self.BASE, code)
        self.write(self.END, bytes.fromhex('4e714e71'))
        self.write(self.STUB, bytes.fromhex('4e75'))
        self.off = {k: self.BASE + v for k, v in off.items()}
        self.state = self.off['_clock_state']

    def write(self, a, b):
        ok(u.uc_mem_write(self.h, a, b, len(b)))

    def read(self, a, n):
        b = C.create_string_buffer(n)
        ok(u.uc_mem_read(self.h, a, b, n))
        return b.raw

    def put(self, a, fmt, v):
        self.write(a, struct.pack('>' + fmt, v))

    def get(self, a, fmt):
        return struct.unpack('>' + fmt, self.read(a, struct.calcsize(fmt)))[0]

    def cs(self, name, v=None):
        o, fmt = CS[name]
        if v is None:
            return self.get(self.state + o, fmt)
        self.put(self.state + o, fmt, v)

    def reg(self, k, v=None):
        x = C.c_uint32(0 if v is None else v & 0xffffffff)
        if v is None:
            ok(u.uc_reg_read(self.h, k, C.byref(x)))
            return x.value
        ok(u.uc_reg_write(self.h, k, C.byref(x)))

    def call(self, name, **regs):
        self.write(self.STACK, struct.pack('>I', self.END))
        self.reg(REG_A7, self.STACK)
        self.reg(REG_A4, A4)
        for k, v in regs.items():
            self.reg({'a0': REG_A0, 'a1': REG_A1, 'a5': REG_A5, 'd0': REG_D0, 'd1': REG_D1}[k], v)
        ok(u.uc_emu_start(self.h, self.off[name], self.END, 0, 1000000))
        assert self.reg(REG_A7) == self.STACK + 4, 'stack unbalanced in ' + name


def fail(what, got, want):
    print('MISMATCH %s\n  68000 %s\n  model %s' % (what, got, want))
    sys.exit(1)


def check_helpers(e):
    n = 0
    for h in range(0, 60000):
        v = to_bcd(h)
        for k in range(10):
            e.put(LAP, 'I', v)
            e.call('_clock_bcd_add', a1=LAP, d1=k)
            if e.get(LAP, 'I') != to_bcd(h + k):
                fail('bcd add %08x + %d' % (v, k), hex(e.get(LAP, 'I')), hex(to_bcd(h + k)))
            if h >= k:
                e.put(LAP, 'I', v)
                e.call('_clock_bcd_sub', a1=LAP, d1=k)
                if e.get(LAP, 'I') != to_bcd(h - k):
                    fail('bcd sub %08x - %d' % (v, k), hex(e.get(LAP, 'I')), hex(to_bcd(h - k)))
            n += 1
    for h in range(0, 600000):
        e.call('_clock_to_bcd', d0=h)
        b = e.reg(REG_D0)
        if b != to_bcd(h):
            fail('to bcd %d' % h, hex(b), hex(to_bcd(h)))
        e.call('_clock_from_bcd', d0=b)
        if e.reg(REG_D0) != h:
            fail('from bcd %08x' % b, e.reg(REG_D0), h)
    print('BCD helpers: %d adds/subtracts and 600000 conversions agree' % n)


class Model:
    """The rules of HardDrivinClock.s in binary hundredths."""

    def __init__(self, e):
        self.e = e

    def load(self):
        e = self.e
        self.s = {k: e.cs(k) for k in CS}
        self.g = dict(lap=from_bcd(e.get(LAP, 'I')), left=from_bcd(e.get(LEFT, 'I')), out=e.get(OUT, 'B'),
                      gate=e.get(GATE, 'B'), race=e.get(RACE, 'B'), started=e.get(STARTED, 'B'),
                      crash=e.get(CRASH, 'B'), replay=e.get(REPLAY, 'B'), phantom=e.get(PHANTOM, 'B'),
                      level=e.get(LEVEL, 'B'), stunt=e.get(STUNT, 'B'), qualified=e.get(QUALIFIED, 'B'),
                      deadline=e.get(DEADLINE, 'I'), speed=e.get(SPEED, 'h'))

    def preset(self):
        lv = self.g['level'] - 1
        return PRESETS[lv if 0 <= lv <= 2 else 0]

    def left_off(self, n):
        s, g = self.s, self.g
        if s['busy']:
            s['pending'] += n
            return
        n += s['pending']
        s['pending'] = 0
        if s['expired']:
            s['overtime'] += n
        elif g['left'] < n:
            s['overtime'] = n - g['left']
            g['left'], g['out'], s['expired'] = 0, 0xff, 0xff
        else:
            g['left'] -= n

    def vbl(self):
        s, g = self.s, self.g
        n = 2
        s['fraction'] += 2262
        if s['fraction'] >= 709379:
            s['fraction'] -= 709379
            n = 3
        if g['phantom']:
            s['handicap'] = 500
        elif not g['race']:
            return 'native'
        if not g['gate']:
            if g['replay']:
                self.crash(n)
            return
        if not g['started']:
            g['lap'] += n
            return
        if g['crash'] or g['replay']:
            self.crash(n)
            return
        g['lap'] += n
        if not g['phantom']:
            self.left_off(n)

    def crash(self, n):
        s = self.s
        if self.g['phantom']:
            return
        t = 5 * n + s['crash']
        s['crash'] = t & 15
        if t >> 4:
            self.left_off(t >> 4)

    def award(self, bonus):
        s, g = self.s, self.g
        if s['expired']:
            rest = bonus - s['overtime']
            s['overtime'] = 0
            if rest <= 0:
                s['overtime'] = -rest
                g['left'], g['out'] = 0, 0xff
                return
            s['expired'] = 0
            total = rest
        else:
            total = g['left'] + bonus
        g['left'] = min(total, self.preset()[0])


def compare(e, m, what, native=False):
    got = Model(e)
    got.load()
    for k in m.g:
        if got.g[k] != m.g[k]:
            fail('%s: %s' % (what, k), got.g[k], m.g[k])
    for k in m.s:
        if got.s[k] != m.s[k]:
            fail('%s: state %s' % (what, k), got.s[k], m.s[k])


def store(e, m):
    g, s = m.g, m.s
    e.put(LAP, 'I', to_bcd(g['lap']))
    e.put(LEFT, 'I', to_bcd(g['left']))
    for a, k in ((OUT, 'out'), (GATE, 'gate'), (RACE, 'race'), (STARTED, 'started'), (CRASH, 'crash'),
                 (REPLAY, 'replay'), (PHANTOM, 'phantom'), (LEVEL, 'level'), (STUNT, 'stunt'),
                 (QUALIFIED, 'qualified')):
        e.put(a, 'B', g[k])
    e.put(DEADLINE, 'I', g['deadline'])
    e.put(SPEED, 'h', g['speed'])
    for k, v in s.items():
        e.cs(k, v)


def check_vbl(e, fields, rnd):
    e.cs('native_lap', Emu.STUB)
    e.cs('native_left', Emu.STUB)
    m = Model(e)
    m.load()
    m.g.update(race=0xff, gate=0xff, started=0, lap=0, left=19200, out=0)
    m.s.update(fraction=0, overtime=0, crash=0, pending=0, expired=0, busy=0, handicap=1000)
    store(e, m)
    counts = dict(prestart=0, running=0, crash=0, replay=0, paused=0, phantom=0, expired=0, busy=0, native=0)
    for i in range(fields):
        g, s = m.g, m.s
        r = rnd.random()
        if r < 0.002:
            g['started'] ^= 0xff
        elif r < 0.004:
            g['crash'] = 0 if g['crash'] else 25
        elif r < 0.006:
            g['replay'] ^= 0xff
            g['gate'] = 0 if g['replay'] else 0xff
        elif r < 0.007:
            g['gate'] ^= 0xff
        elif r < 0.008:
            g['phantom'] ^= 0xff
        elif r < 0.009:
            g['race'] ^= 0xff
        elif r < 0.012:
            s['busy'] ^= 0xff
        elif r < 0.013:
            g['left'] = rnd.choice((rnd.randint(0, 40), rnd.randint(0, 19200)))
            g['out'], s['expired'], s['overtime'] = 0, 0, 0
        g['lap'] = min(g['lap'], 500000)
        store(e, m)
        e.call('_clock_vbl')
        how = m.vbl()
        compare(e, m, 'vbl field %d' % i)
        key = ('native' if how == 'native' else 'phantom' if g['phantom'] else 'paused' if not g['gate'] and
               not g['replay'] else 'replay' if g['replay'] else 'prestart' if not g['started'] else 'crash'
               if g['crash'] else 'busy' if s['busy'] else 'expired' if s['expired'] else 'running')
        counts[key] += 1
    print('VBL: %d fields agree (%s)' % (fields, ', '.join('%s %d' % kv for kv in counts.items())))


def check_events(e, n, rnd):
    m = Model(e)
    done = dict(checkpoint=0, finish=0, init=0, auto=0, button=0, offroad=0, left=0, expired=0, champion=0)
    for i in range(n):
        m.load()
        g, s = m.g, m.s
        g.update(level=rnd.choice((0, 1, 2, 3, 4)), stunt=rnd.choice((0, 1)), qualified=rnd.choice((0, 0xff)),
                 left=rnd.randint(0, 19200), lap=rnd.randint(0, 40000), started=rnd.choice((0, 0xff)),
                 speed=rnd.randint(-40, 40) * rnd.choice((1, 1, 20)), out=0,
                 deadline=rnd.choice((0, to_bcd(rnd.randint(0, 45000)))), race=0xff)
        s.update(expired=0, overtime=0, busy=0, finishes=rnd.randint(0, 5), handicap=rnd.randint(500, 1000),
                 played=rnd.choice((0, 0xff)), qualified=rnd.choice((0, 0xff)), champion=rnd.randint(9000, 30000),
                 pending=0, crash=rnd.randint(0, 15))
        if rnd.random() < 0.3:
            g['left'], g['out'], s['expired'], s['overtime'] = 0, 0xff, 0xff, rnd.randint(0, 1000)
        if rnd.random() < 0.02:
            s['overtime'] = rnd.randint(5000, 20000)
        store(e, m)
        what = rnd.choice(list(done))
        if what == 'checkpoint':
            m.award(2900 if g['stunt'] else 3200)
            e.call('_clock_checkpoint')
        elif what == 'finish':
            if g['qualified']:
                s['qualified'] = 0xff
            p = m.preset()
            m.award(p[1 + min(s['finishes'], 2)])
            s['finishes'] += 1
            if g['deadline']:
                g['deadline'] = to_bcd(max(1, from_bcd(g['deadline']) - g['lap']))
            e.call('_clock_finish')
        elif what == 'init':
            s.update(overtime=0, expired=0, finishes=0, crash=0, pending=0)
            if s['played'] and not s['qualified']:
                s['handicap'] = min(s['handicap'] + 50, 1000)
            s.update(played=0xff, qualified=0)
            g['left'] = m.preset()[0]
            e.call('_clock_race_init')
            if e.get(CHAMP, 'I') != to_bcd(s['champion']) or e.get(QUAL, 'I') != to_bcd(s['champion'] + s['handicap']):
                fail('race init champion/qualifying', (hex(e.get(CHAMP, 'I')), hex(e.get(QUAL, 'I'))),
                     (hex(to_bcd(s['champion'])), hex(to_bcd(s['champion'] + s['handicap']))))
        elif what == 'auto':
            g['left'] = m.preset()[0]
            e.call('_clock_auto_start')
        elif what == 'button':
            if not g['started']:
                g.update(started=0xff, lap=0, left=m.preset()[0])
            e.call('_clock_button_start')
        elif what == 'offroad':
            g['deadline'] = to_bcd(from_bcd(g['deadline']) + 1100)
            e.call('_clock_offroad')
        elif what == 'left':
            want = to_bcd(max(0, from_bcd(g['deadline']) - g['lap']))
            e.call('_clock_offroad_left', a5=A5, d1=0x12345678)
            got = (e.reg(REG_D0), e.get(A5 - 4, 'I'), e.reg(REG_D1))
            if got != (want, want, 0x12345678):
                fail('off-road time left %08x - %08x' % (g['deadline'], to_bcd(g['lap'])),
                     tuple(hex(x) for x in got), (hex(want), hex(want), '0x12345678'))
        elif what == 'expired':
            g['out'] = rnd.choice((0, 0xff))
            store(e, m)
            if g['out'] and (abs(g['speed']) < 12 or s['overtime'] >= 1000):
                g['race'] = 0
            e.call('_clock_expired')
        elif what == 'champion':
            s['champion'] = g['lap']
            e.call('_clock_champion')
            if e.get(CHAMP, 'I') != to_bcd(g['lap']):
                fail('champion G($af00)', hex(e.get(CHAMP, 'I')), hex(to_bcd(g['lap'])))
        compare(e, m, '%s %d' % (what, i))
        done[what] += 1
    print('Events: %d calls agree (%s)' % (n, ', '.join('%s %d' % kv for kv in done.items())))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('slave')
    ap.add_argument('listing')
    ap.add_argument('--fields', type=int, default=200000)
    ap.add_argument('--events', type=int, default=50000)
    ap.add_argument('--seed', type=int, default=1)
    a = ap.parse_args()
    e = Emu(code_hunk(a.slave), label_offsets(a.listing, ROUTINES))
    rnd = random.Random(a.seed)
    try:
        check_helpers(e)
        check_vbl(e, a.fields, rnd)
        check_events(e, a.events, rnd)
    finally:
        ok(u.uc_close(e.h))


if __name__ == '__main__':
    main()
