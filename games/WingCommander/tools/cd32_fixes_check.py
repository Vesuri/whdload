#!/usr/bin/env python3
"""Native check of the CD32 release fixes on both languages.

Bunk save: the game's own slot save (E:275de, G:277a0)
runs on the pinned executables after the slave's patch lists are applied, with
WHDLoad's file calls modelled by a file dictionary.

Psygore's list alone is the negative control: the save is written but the
slot's name is cleared. The release build's extra list must keep the name,
return success and enumerate existing Bed_N files. TrainSim: the fly-off call
must receive the key choice; the unfixed list passes -1. Mouse: the native room routine
runs from after its input call to its sprite move with the slave's position
hook, the RAWMOUSE callback moves the native sprite, the room exit stops it and
the VBL pad read adds the left button as fire. High scores: a pilot save also
writes the six-entry table to Bed_N.hi, and the game's own pilot restore
(E:26874, G:26a20) loads it back only when it is valid; without it the table is
unchanged. Game bytes stay in tmp/.
"""
import argparse, ctypes as C, hashlib, json, re, struct
from pathlib import Path
from c2p_check import u, ck, P, I, Q, Z
from runtime_buffers import load as load_slave

u.uc_emu_stop.argtypes = [P]; u.uc_emu_stop.restype = I

ROOT = Path(__file__).resolve().parents[1]
GAMES = {
    'english': dict(path='tmp/game/WingCommanderCD32/data/wing.english',
                    sha='093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657',
                    psygore=0x15e6, fix='fix_patch_en', save=0x275de, a4=0x7ffe,
                    app=-1332, prefix=-1328, name=-1296,
                    sites=dict(store=0x31498, list=0x314b0, branch=0x276b0), trainsim=0x1827e, flyoff=0x17d06,
                    scores=dict(site=0x268be, restore=0x26874, table=17664, stubs=(0x6, 0x2543c)),
                    mouse=dict(room=0x273fc, exit=0x27362, pad=0x33e78, guard=0x33de6, reset=0x33ddc, entry=0x2737c, move=0x27418,
                               leave=0x2735a, left=0x27368, pos=2696, rect=2728, flags=18116,
                               slot=162, hide=-1160, image=-1164, gfx=-778, params='mouse_params_en',
                               name=0x16ed0, step=0x16c66, sel=17716, cols=17706)),
    'german': dict(path='tmp/game/WingCommanderCD32/data/wing.german',
                   sha='2047da69f2c83803675921afd86204747609a5c59dd3e7f67d954d785677dabe',
                   psygore=0x1cf4, fix='fix_patch_de', save=0x277a0, a4=0x7ffe,
                   app=-1288, prefix=-1284, name=-1252,
                   sites=dict(store=0x3165a, list=0x31672, branch=0x27872), trainsim=0x18338, flyoff=0x17db6,
                   scores=dict(site=0x26a6a, restore=0x26a20, table=17714, stubs=(0x6, 0x255bc)),
                   mouse=dict(room=0x275be, exit=0x27524, pad=0x3403a, guard=0x33fa8, reset=0x33f9e, entry=0x2753e, move=0x275da,
                              leave=0x2751c, left=0x2752a, pos=2740, rect=2772, flags=18166,
                              slot=206, hide=-1116, image=-1120, gfx=-734, params='mouse_params_de',
                              name=0x16f6e, step=0x16d04, sel=17766, cols=17756)),
}
SLAVE = 0x200000          # slave payload
RES = 0x280000            # resload jump table, each entry an RTS
DATA = 0x300000           # game A4 data area (A4 = DATA + 0x8000)
SLOTS = 0x320000          # 8 x 116-byte slot records
STRINGS = 0x330000
STACK = 0x3f0000
STOP = 0x3fff00
RECT = 0x340000           # room rectangle record (+24..+30)
IMAGE = 0x340100          # pointer image record, hotspot at +4/+6
GFX = 0x341000            # graphics base; MoveSprite at -426
EVENT = 0x342000          # InputEvent
CALLS = {12: 'SaveFile', 36: 'GetFileSize', 88: 'DeleteFile', 8: 'LoadFile'}


def hunk0(cfg):
    raw = (ROOT/cfg['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != cfg['sha']:
        raise ValueError(cfg['path']+': unsupported executable')
    assert struct.unpack_from('>I', raw, 0x24)[0] == 0x3e9
    size = struct.unpack_from('>I', raw, 0x28)[0]*4
    return bytearray(raw[0x2c:0x2c+size])


def apply(blob, start, code, log):
    """Apply a WHDLoad patch list (the commands these lists use); PL_P/PL_PS
    targets are words relative to the list start."""
    at = start
    while True:
        cmd = struct.unpack_from('>H', blob, at)[0]
        if cmd == 0:
            return
        if cmd & 0x8000:
            off = struct.unpack_from('>H', blob, at+2)[0]; at += 4
        else:
            off = struct.unpack_from('>I', blob, at+2)[0]; at += 6
        cmd &= 0x7fff
        if cmd == 1:
            code[off:off+2] = b'\x4e\x75'
        elif cmd in (2, 3):
            rel = struct.unpack_from('>h', blob, at)[0]; at += 2
            code[off:off+6] = struct.pack('>HI', 0x4ef9 if cmd == 2 else 0x4eb9, SLAVE+start+rel)
        elif cmd == 4:
            at += 2             # PL_S: not on the save path
        elif cmd == 7:
            code[off:off+2] = blob[at:at+2]; at += 2
        elif cmd == 8:
            code[off:off+4] = blob[at:at+4]; at += 4
        elif cmd == 0xb:
            n = struct.unpack_from('>H', blob, at)[0]; at += 2
            code[off:off+n] = b'\x4e\x71'*(n//2)
        else:
            raise ValueError(f'patch command {cmd:#x}')
        log.append((cmd, off))


class Machine:
    def __init__(self, code, blob, cfg, files):
        self.h = P(); ck(u.uc_open(7, 1 << 30, C.byref(self.h)))
        ck(u.uc_ctl(self.h, 7 | (1 << 26) | (1 << 30), I(2)))     # 68020
        ck(u.uc_mem_map(self.h, 0, 0x400000, 7))
        self.cfg, self.files, self.calls = cfg, files, []
        self.write(0, bytes(code)); self.write(SLAVE, blob)
        self.write(SLAVE+0x121e, struct.pack('>I', RES))
        self.write(RES, b'\x4e\x75'*128)
        self.a4 = DATA+0x8000
        self.write(STRINGS, b'WC1\0'); self.write(STRINGS+16, b'Bed_\0')
        self.write(self.a4+cfg['app'], struct.pack('>I', STRINGS))
        self.write(self.a4+cfg['prefix'], struct.pack('>I', STRINGS+16))
        self.write(0x14246, b'\x4e\x75')    # slot-screen helper, not on the save path
        self.reg(17, 0x2700)

        def hook(h, address, size, data):
            off = address-RES
            name = CALLS.get(off)
            if name is None:
                self.calls.append(('unexpected', off)); ck(u.uc_emu_stop(self.h)); return
            if name == 'GetFileSize':
                f = self.string(self.reg(1)); self.reg(9, len(self.files.get(f, b'')))
            elif name == 'SaveFile':
                f = self.string(self.reg(1)); n = self.reg(9)
                self.files[f] = self.read(self.reg(2), n); self.reg(9, 0)
            elif name == 'DeleteFile':
                f = self.string(self.reg(1)); self.files.pop(f, None); self.reg(9, -1 & 0xffffffff)
            else:                                       # LoadFile: whole file to a1
                f = self.string(self.reg(1)); data = self.files[f]
                self.write(self.reg(2), data); self.reg(9, len(data))
            self.calls.append((name, f))
        self.cb = C.CFUNCTYPE(None, P, Q, C.c_uint32, P)(hook)
        handle = Z(); ck(u.uc_hook_add(self.h, C.byref(handle), 4, self.cb, None, RES, RES+255))
        self.moves = []
        self.write(GFX-426, b'\x4e\x75')

        def move(h, address, size, data):
            self.moves.append((C.c_int16(self.reg(9)).value, C.c_int16(self.reg(10)).value, self.reg(1), self.reg(2)))
        self.mcb = C.CFUNCTYPE(None, P, Q, C.c_uint32, P)(move)
        handle = Z(); ck(u.uc_hook_add(self.h, C.byref(handle), 4, self.mcb, None, GFX-426, GFX-425))

    def write(self, a, b): ck(u.uc_mem_write(self.h, a, bytes(b), len(b)))

    def read(self, a, n):
        b = C.create_string_buffer(n); ck(u.uc_mem_read(self.h, a, b, n)); return b.raw

    def reg(self, r, v=None):
        x = C.c_uint32(v or 0)
        ck(u.uc_reg_read(self.h, r, C.byref(x)) if v is None else u.uc_reg_write(self.h, r, C.byref(x)))
        return x.value

    def string(self, a):
        return self.read(a, 64).split(b'\0')[0].decode('latin-1')

    def call(self, entry, args, regs=()):
        sp = STACK-len(args)-4
        self.write(sp, struct.pack('>I', STOP)+args)
        self.write(STOP, b'\x4e\x71')
        self.reg(8, sp); self.reg(5, self.a4)
        for r, v in regs:
            self.reg(r, v)
        ck(u.uc_emu_start(self.h, entry, STOP, 0, 2000000))
        assert self.reg(18) == STOP, hex(self.reg(18))
        assert self.reg(8) == sp+4, 'stack not balanced'
        assert self.reg(5) == self.a4
        return self.reg(9)

    def close(self): ck(u.uc_close(self.h))


TABLE = bytes.fromhex('0300 00004e20 0800 00003a98 0b00 00002ee0 0100 00001f40 0d00 00000fa0 0500 00000064'.replace(' ', ''))


def save(cfg, code, blob, files, slot, name):
    m = Machine(code, blob, cfg, files)
    m.write(m.a4+cfg['scores']['table'], TABLE)
    records = bytearray(8*116)
    for n in range(8):
        records[n*116:n*116+116] = bytes([0x41+n])+bytes([n])*115
    records[slot*116] = name
    m.write(SLOTS, records)
    sentinel = [(11, 0x11111111), (12, 0x22222222), (13, 0x33333333), (14, 0x44444444),
                (15, 0x55555555), (16, 0x66666666), (3, 0x77777777), (4, 0x88888888)]
    result = m.call(cfg['save'], struct.pack('>Ih', SLOTS, slot), sentinel) & 0xffff
    for r, v in sentinel:
        assert m.reg(r) == v, f'register {r} not preserved'
    after = m.read(SLOTS, 8*116); calls = m.calls; m.close()
    return result, after, calls


def restore(cfg, code, blob, files, slot, table):
    """The game's pilot restore for bed slot (d2, as its caller leaves it);
    returns the table afterwards and the file calls."""
    sc = cfg['scores']
    code = bytearray(code)
    for stub in sc['stubs']:
        code[stub:stub+2] = b'\x4e\x75'
    m = Machine(code, blob, cfg, files)
    m.write(m.a4+sc['table'], table)
    m.write(m.a4-32716, b'\0\0')
    m.write(SLOTS, bytes(range(116)))
    # d2 the bed; d3-d7, a2, a3, a5 and a6 must survive (a4 is checked by call).
    keep = [(12, 0x33333333), (13, 0x44444444), (14, 0x55555555), (15, 0x66666666),
            (16, 0x77777777), (3, 0x22222222), (4, 0x23232323), (6, 0x25252525), (7, 0x26262626)]
    m.call(sc['restore'], struct.pack('>III', SLOTS, SLOTS+0x400, SLOTS+0x800), [(11, slot)]+keep)
    assert m.reg(11) == slot, 'd2 not preserved'
    for r, v in keep:
        assert m.reg(r) == v, f'register {r} not preserved'
    assert m.read(m.a4-32716, 2) == b'\0\1', 'replaced store missing'
    assert m.read(SLOTS+0x800, 64) == bytes(range(2, 66)), 'record copy changed'
    after = m.read(m.a4+sc['table'], 36); calls = m.calls; m.close()
    return after, calls


def nvlist(cfg, code, blob, files, count):
    m = Machine(code, blob, cfg, files)
    m.write(SLOTS, b'\x5a'*32)
    m.call(cfg['sites']['list'], struct.pack('>Ih', SLOTS, count))
    out = m.read(SLOTS, 32); calls = m.calls; m.close()
    return out, calls


def flyoff_choice(cfg, code, blob, choice, pointer):
    """Run from the fly-off call site to the animation's entry; return its
    choice argument."""
    m = Machine(code, blob, cfg, {})
    m.write(SLOTS, struct.pack('>h', choice))
    m.reg(3, SLOTS); m.reg(13, pointer & 0xffffffff)
    m.reg(8, STACK); m.reg(5, m.a4)
    ck(u.uc_emu_start(m.h, cfg['trainsim'], cfg['flyoff'], 0, 1000))
    assert m.reg(18) == cfg['flyoff']
    sp = m.reg(8)
    arg = struct.unpack('>h', m.read(sp+8, 2))[0]
    m.close()
    return arg


def mouse_cases(cfg, psy, fixed, blob, sy):
    """Room routine with the position hook, RAWMOUSE callback, room exit and
    the VBL pad read with the left button."""
    mc = cfg['mouse']
    m = Machine(fixed, blob, cfg, {})
    for hw in (0xbfe000, 0xdff000):
        ck(u.uc_mem_map(m.h, hw, 0x1000, 3))
    a4 = m.a4
    w = lambda off, fmt, *v: m.write(a4+off, struct.pack(fmt, *v))
    rd = lambda off: struct.unpack('>hh', m.read(a4+off, 4))
    var = lambda name: struct.unpack('>h', m.read(SLAVE+sy[name], 2))[0]
    m.write(RECT+24, struct.pack('>4h', 40, 30, 280, 180))
    m.write(IMAGE+4, struct.pack('>hh', -3, -2))
    w(mc['rect'], '>I', RECT); w(mc['image'], '>I', IMAGE); w(mc['gfx'], '>I', GFX)
    w(mc['hide'], '>h', 0); w(mc['pos'], '>hh', 160, 100); w(-13484 if cfg is GAMES['english'] else -13440, '>I', 0)
    m.call(SLAVE+sy['mouse_init'], b'', [(1, SLAVE+sy[mc['params']]), (9, 0)])

    def room(stick=(0, 0, 0, 0)):
        m.write(a4+mc['flags'], bytes(stick))
        m.reg(8, STACK); m.reg(5, a4)
        ck(u.uc_emu_start(m.h, mc['entry'], mc['move'], 0, 10000))
        assert m.reg(18) == mc['move']
        got = rd(mc['pos'])
        assert (C.c_int16(m.reg(11)).value, C.c_int16(m.reg(12)).value) == got
        return got

    def event(dx, dy, qualifier=0x8000):
        m.write(EVENT, struct.pack('>IBBHHhh', 0, 2, 0, 0xff, qualifier, dx, dy))
        before = len(m.moves)
        m.call(SLAVE+sy['mouse_event'], b'', [(4, EVENT)])
        return m.moves[before:]

    out = {}
    assert event(8, 8) == [], 'callback active before the room routine ran'
    assert room() == (160, 100) and var('mouse_active') == 1
    assert struct.unpack('>I', m.read(a4+mc['slot'], 4))[0] == SLAVE+sy['mouse_event']
    assert (var('mouse_x'), var('mouse_y')) == (320, 200)
    # Each event moves the sprite at once: room position plus image hotspot.
    assert [x[:2] for x in event(10, -6)] == [(165-3, 97-2)]
    assert [x[:2] for x in event(1, 1)] == [(165-3, 97-2)]      # half pixels accumulate
    assert [x[:2] for x in event(1, 1)] == [(166-3, 98-2)]
    assert room() == (166, 98), 'room routine did not take the mouse position'
    assert room() == (166, 98)
    # Stick and keys still step it; the mouse continues from there.
    assert room((1, 0, 0, 0)) == (161, 98) and room((0, 0, 0, 1)) == (161, 101)
    assert [x[:2] for x in event(4, 0)] == [(163-3, 101-2)]
    assert room() == (163, 101)
    # Clamped to the room rectangle.
    assert [x[:2] for x in event(-127, -127)] + [x[:2] for x in event(-127, -127)] == [(99-3, 37-2), (40-3, 30-2)]
    for _ in range(4):
        moves = event(127, 127)
    assert [x[:2] for x in moves] == [(280-3, 180-2)] and room() == (280, 180)
    out['motion'] = 'pass'
    # Ignored: absolute events, empty motion, hidden pointer.
    assert event(5, 5, 0) == [] and event(0, 0) == []
    w(mc['hide'], '>h', 0x4000)
    assert event(-50, -50) == [] and room() == (280, 180)
    w(mc['hide'], '>h', 0)
    out['ignored'] = 'pass'
    # Room exit: native move off screen, callback inactive, next room resyncs.
    m.write(STACK-8, struct.pack('>I', STOP))
    m.reg(8, STACK-8); m.reg(5, a4)
    ck(u.uc_emu_start(m.h, mc['leave'], mc['left'], 0, 10000))
    assert m.reg(18) == mc['left'] and [x[:2] for x in m.moves[-1:]] == [(1000-3, 1000-2)]
    assert var('mouse_active') == 0 and event(-40, -40) == []
    w(mc['pos'], '>hh', 100, 60)
    assert room() == (100, 60) and (var('mouse_x'), var('mouse_y')) == (200, 120)
    out['exit'] = 'pass'
    m.close()
    # VBL pad read: the left button (CIA-A bit 6 low) adds the red button.
    pads = {}
    for name, code in (('psygore', psy), ('fixed', fixed)):
        for lmb in (0, 1):
            m = Machine(code, blob, cfg, {})
            for hw in (0xbfe000, 0xdff000):
                ck(u.uc_mem_map(m.h, hw, 0x1000, 3))
            m.write(0xbfe001, bytes([0xbf if lmb else 0xff]))
            m.reg(8, STACK)
            ck(u.uc_emu_start(m.h, mc['pad'], mc['pad']+6, 0, 10000))
            assert m.reg(18) == mc['pad']+6
            pads[name, lmb] = m.reg(9); m.close()
    assert pads['psygore', 0] & (1 << 22) == 0 and pads['psygore', 1] == pads['psygore', 0]
    assert pads['fixed', 0] == pads['psygore', 0] and pads['fixed', 1] == pads['psygore', 0] | (1 << 22)
    out['left_button'] = 'pass'
    # Pad record reset: the release guard (counter -1) only while a fire
    # button is held; Psygore's list keeps it always.
    for name, code in (('psygore', psy), ('fixed', fixed)):
        for pra, held in ((0xff, False), (0xbf, True), (0x7f, True)):
            m = Machine(code, blob, cfg, {})
            ck(u.uc_mem_map(m.h, 0xbfe000, 0x1000, 3))
            m.write(0xbfe001, bytes([pra])); m.write(RECT, b'\x5a'*20)
            m.call(mc['reset'], b'', [(1, RECT)])
            record = m.read(RECT, 20); m.close()
            assert record[:18] == bytes(18), record
            want = -1 if held or name == 'psygore' else 0
            assert struct.unpack('>h', record[18:])[0] == want, (name, hex(pra), record)
    out['click_guard'] = 'pass'
    out['name_entry'] = name_cases(cfg, fixed, blob, sy)
    return out


def name_cases(cfg, fixed, blob, sy):
    """Name entry grid poll: the slave's hook and the native grid step, from
    the hook site to the native redraw call."""
    mc = cfg['mouse']; cols = 10
    m = Machine(fixed, blob, cfg, {})
    a4 = m.a4
    m.call(SLAVE+sy['mouse_init'], b'', [(1, SLAVE+sy[mc['params']]), (9, 0)])
    assert struct.unpack('>I', m.read(SLAVE+sy['name_step'], 4))[0] == 0     # set by release_patchseg
    m.write(SLAVE+sy['name_step'], struct.pack('>I', mc['step']))
    m.write(a4+mc['cols'], struct.pack('>h', cols))
    fields = [100]

    def event(dx, dy):
        m.write(EVENT, struct.pack('>IBBHHhh', 0, 2, 0, 0xff, 0x8000, dx, dy))
        m.call(SLAVE+sy['mouse_event'], b'', [(4, EVENT)])

    def poll(stick=(0, 0), gap=1):
        fields[0] += gap
        m.write(SLAVE+sy['mouse_fields'], struct.pack('>H', fields[0] & 0xffff))
        m.write(STACK-2, struct.pack('>h', stick[1]))
        m.reg(8, STACK-2); m.reg(5, a4); m.reg(9, stick[0] & 0xffff)
        ck(u.uc_emu_start(m.h, mc['name'], mc['name']+6, 0, 10000))
        assert m.reg(18) == mc['name']+6 and m.reg(8) == STACK-4, 'stack differs from the native call'
        cell = struct.unpack('>h', m.read(a4+mc['sel'], 2))[0]-32
        return cell % cols, cell // cols

    def at(col, row):
        m.write(a4+mc['sel'], struct.pack('>h', 32+row*cols+col))

    at(3, 4)
    event(200, 200)
    assert poll(gap=50) == (3, 4), 'motion from another screen moved the box'
    assert struct.unpack('>I', m.read(a4+mc['slot'], 4))[0] == SLAVE+sy['mouse_event']
    event(36, 0); assert poll() == (5, 4)
    event(17, 0); assert poll() == (5, 4)          # less than a cell
    event(1, 0); assert poll() == (6, 4)
    event(-17, 0); assert poll() == (6, 4)
    event(-1, 0); assert poll() == (5, 4)
    event(0, 36); assert poll() == (5, 6)
    event(0, -18); assert poll() == (5, 5)
    # Columns stop at the edge and drop the rest; the stick still wraps.
    event(1000, 0); assert poll() == (9, 5)
    event(-18, 0); assert poll() == (8, 5)
    event(-1000, 0); assert poll() == (0, 5)
    assert poll((-1, 0)) == (9, 5) and poll((1, 0)) == (0, 5) and poll((0, 1)) == (0, 6)
    # The native step clamps rows.
    event(0, -1000); assert poll() == (0, 0)
    event(30, 0); poll()
    event(30, 0); assert poll(gap=20) == (1, 0), 'stale motion kept after a gap'
    m.close()
    return 'pass'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--sabotage', choices=('store-failure', 'list-stub', 'mouse-ignored', 'name-ignored', 'scores-ignored'),
                   help='negative control: the check must fail')
    a = p.parse_args()
    out = a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new tmp report required')
    meta = json.loads((a.build/'build.json').read_text())
    slave = (a.build/'WingCommanderCD32.Slave').read_bytes()
    assert hashlib.sha256(slave).hexdigest() == meta['sha256'] and meta['release']
    blob = load_slave(slave)
    sy = {n: int(o, 16) for o, n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
    if a.sabotage:
        blob = bytearray(blob)
        if a.sabotage == 'store-failure':   # Psygore's return value
            at = blob.index(bytes.fromhex('7000'), sy['bunk_store'], sy['bunk_list_en'])
            blob[at:at+2] = bytes.fromhex('7001')
        elif a.sabotage == 'mouse-ignored':  # room routine never takes the mouse position
            at = sy['mouse_room']
            while blob[at] != 0x66:
                at += 2
            blob[at:at+2] = bytes.fromhex('4e71')
        elif a.sabotage == 'name-ignored':  # name entry drops the mouse's column steps
            at = blob.index(bytes.fromhex('d36f001c'), sy['mouse_name'])
            blob[at:at+4] = bytes.fromhex('4e714e71')
        elif a.sabotage == 'scores-ignored':  # restore never copies the table file
            at = blob.index(bytes.fromhex('32d8'), sy['scores_load'])
            blob[at:at+2] = bytes.fromhex('4e71')
        else:                               # Psygore's PL_R
            blob[sy['bunk_list']:sy['bunk_list']+4] = bytes.fromhex('4cdf0c04')
            blob[sy['bunk_list']+4:sy['bunk_list']+6] = bytes.fromhex('4e75')
        blob = bytes(blob)
    report = {}
    for lang, cfg in GAMES.items():
        original = hunk0(cfg)
        s = cfg['sites']
        # The sites hold the bytes the patches assume.
        assert original[s['store']:s['store']+6] == bytes.fromhex('720106400009')
        assert original[s['list']:s['list']+4] == bytes.fromhex('48e70036')
        assert original[s['branch']:s['branch']+2] == bytes.fromhex('6604')
        psy = bytearray(original); log = []
        apply(blob, cfg['psygore'], psy, log)
        assert (0xb, s['branch']) in log and (1, s['list']) in log and (3, s['store']) in log
        fixed = bytearray(psy); fixlog = []
        apply(blob, sy[cfg['fix']], fixed, fixlog)
        mc = cfg['mouse']
        sc = cfg['scores']
        assert fixlog == [(3, s['store']), (2, s['list']), (7, s['branch']), (7, cfg['trainsim']),
                          (3, mc['room']), (3, mc['exit']), (3, mc['pad']), (3, mc['guard']), (3, mc['name']),
                          (3, sc['site'])], fixlog
        assert original[sc['site']:sc['site']+6] == bytes.fromhex('397c00018034')
        assert original[sc['restore']:sc['restore']+4] == bytes.fromhex('48e70030')
        assert all(original[x:x+2] == b'\x4e\xb9' for x in (sc['site']-12, sc['site']-6))
        assert original[mc['name']:mc['name']+4] == bytes.fromhex('3f004eba')
        assert original[mc['reset']:mc['guard']+8] == bytes.fromhex('224870094259 51c8fffc 317cffff0012 4e75'.replace(' ', ''))
        assert original[mc['room']:mc['room']+8] == struct.pack('>HhHh', 0x3942, mc['pos'], 0x3943, mc['pos']+2)
        assert original[mc['exit']:mc['exit']+2] == bytes.fromhex('4eb9')
        assert original[mc['leave']:mc['leave']+8] == bytes.fromhex('3f3c03e83f3c03e8')
        assert psy[mc['pad']:mc['pad']+2] == bytes.fromhex('4eb9')
        assert fixed[s['branch']:s['branch']+2] == bytes.fromhex('6604')
        # TrainSim: move.w d4,-(sp) -> move.w (a2),-(sp), before pea/jsr fly-off.
        t = cfg['trainsim']
        assert original[t:t+4] == bytes.fromhex('3f04486c') and original[t+6:t+8] == bytes.fromhex('4eba')
        assert fixed[t:t+2] == bytes.fromhex('3f12') and fixed[t+2:t+8] == original[t+2:t+8]
        changed = [i for i in range(len(psy)) if psy[i] != fixed[i]]
        assert all(any(x <= i < x+6 for x in list(s.values())+[mc['room'], mc['exit'], mc['pad'], mc['guard'], mc['name'], sc['site']]) or t <= i < t+2
                   for i in changed)
        cases = {}
        # Negative control: Psygore's list writes the file but clears the name.
        files = {'Bed_0': b'\0'*116, 'Bed_5': b'\5'*116}
        r, after, calls = save(cfg, psy, blob, files, 3, 0x58)
        assert files.get('Bed_3', b'')[:1] == b'X' and after[3*116] == 0, 'control did not show the bug'
        cases['psygore_new'] = dict(result=r, name_kept=after[3*116] != 0, files=sorted(files))
        # Fixed: new, overwritten and second-digit-free slots keep their names.
        for case, slot, files in (('new', 3, {'Bed_0': b'\0'*116, 'Bed_5': b'\5'*116}),
                                  ('overwrite', 5, {'Bed_0': b'\0'*116, 'Bed_5': b'\5'*116}),
                                  ('first', 0, {}),
                                  ('full', 7, {f'Bed_{n}': bytes([n])*116 for n in range(8)})):
            before = dict(files)
            r, after, calls = save(cfg, fixed, blob, files, slot, 0x58)
            assert r == 1, (case, r)
            assert after[slot*116] == 0x58, (case, 'name cleared')
            record = files[f'Bed_{slot}']
            assert len(record) == 116 and record == after[slot*116:slot*116+116]
            for n, data in before.items():
                if n != f'Bed_{slot}':
                    assert files[n] == data, (case, n, 'other save changed')
            # The pilot's table is saved beside the record.
            assert files[f'Bed_{slot}.hi'] == TABLE, (case, 'table not saved')
            assert set(files) == set(before) | {f'Bed_{slot}', f'Bed_{slot}.hi'}
            assert not any(c[0] in ('DeleteFile', 'unexpected') for c in calls), (case, calls)
            sizes = [c[1] for c in calls if c[0] == 'GetFileSize']
            assert sizes == [f'Bed_{n}' for n in range(8)]*2, sizes
            cases[case] = dict(result=r, files=sorted(files))
        # An emptied slot is deleted, as in Psygore's slave.
        files = {'Bed_2': b'\2'*116, 'Bed_4': b'\4'*116}
        r, after, calls = save(cfg, fixed, blob, files, 2, 0)
        assert 'Bed_2' not in files and files['Bed_4'] == b'\4'*116 and r == 1
        assert not any(n.endswith('.hi') for n in files), files
        cases['delete'] = dict(result=r, files=sorted(files))
        # Pilot restore: a valid table file replaces the table; a missing,
        # wrong-sized or invalid one leaves the game's table as it was.
        seeded = bytes.fromhex('0200 00003a98 0600 00002ee0 0a00 00001f40 0400 00000fa0 0c00 000007d0 0800 00000000'.replace(' ', ''))
        def bad(i, value):
            b = bytearray(TABLE); b[i:i+len(value)] = value; return bytes(b)
        tables = dict(valid=(TABLE, TABLE), absent=(None, seeded), short=(TABLE[:30], seeded), long=(TABLE+b'\0\0', seeded),
                      id_range=(bad(12, b'\x0e'), seeded), repeated=(bad(12, b'\x03'), seeded),
                      negative=(bad(32, b'\xff\xff\xff\xff'), seeded), unsorted=(bad(8, b'\x00\x00\x60\x00'), seeded),
                      unused=(bad(30, b'\xff'), bad(30, b'\xff')))
        for case, (content, want) in tables.items():
            for slot in (0, 3, 10):
                files = {f'Bed_{slot}': b'X'*116, 'Bed_1.hi': seeded[::-1]}
                if content is not None:
                    files[f'Bed_{slot}.hi'] = content
                got, calls = restore(cfg, fixed, blob, files, slot, seeded)
                assert got == want, (case, slot, got.hex())
                assert calls[0] == ('GetFileSize', f'Bed_{slot}.hi'), calls
                assert all(c[0] in ('GetFileSize', 'LoadFile') for c in calls), calls
            # Psygore's list: the restore leaves the table alone.
            got, calls = restore(cfg, psy, blob, files, slot, seeded)
            assert got == seeded and calls == []
        cases['scores'] = sorted(tables)
        # Enumeration alone: flags only below count, two-digit names, rest untouched.
        files = {'Bed_0': b'x', 'Bed_3': b'x', 'Bed_7': b'x', 'Bed_10': b'x', 'Bed_12': b'x', 'Bed_x': b'x'}
        flags, calls = nvlist(cfg, fixed, blob, files, 8)
        assert flags[:8] == bytes([0xff, 0, 0, 0xff, 0, 0, 0, 0xff]) and flags[8:] == b'\x5a'*24
        flags, calls = nvlist(cfg, fixed, blob, files, 12)
        assert flags[:12] == bytes([0xff, 0, 0, 0xff, 0, 0, 0, 0xff, 0, 0, 0xff, 0]) and flags[12:] == b'\x5a'*20
        assert [c[1] for c in calls] == [f'Bed_{n}' for n in range(12)]
        flags, calls = nvlist(cfg, fixed, blob, files, 0)
        assert flags == b'\x5a'*32 and calls == []
        cases['enumeration'] = 'pass'
        # TrainSim: keys 1-4 store 0-3 in (a2) and leave the pointer result -1;
        # a pointer choice stores the same value in both.
        for k in range(4):
            assert flyoff_choice(cfg, psy, blob, k, -1) == -1, 'control did not show the bug'
            assert flyoff_choice(cfg, fixed, blob, k, -1) == k
            assert flyoff_choice(cfg, fixed, blob, k, k) == k
        cases['trainsim'] = 'pass'
        cases['mouse'] = mouse_cases(cfg, psy, fixed, blob, sy)
        report[lang] = cases
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(sha256=meta['sha256'], games=report), indent=2)+'\n')
    print(json.dumps(dict(pass_=True, sha256=meta['sha256'])))


if __name__ == '__main__':
    main()
