#!/usr/bin/env python3
"""Native check of the CD32 release fixes on both languages.

Bunk save: the game's own slot save (E:275de, G:277a0)
runs on the pinned executables after the slave's patch lists are applied, with
WHDLoad's file calls modelled by a file dictionary.

Psygore's list alone is the negative control: the save is written but the
slot's name is cleared. The release build's extra list must keep the name,
return success and enumerate existing Bed_N files. TrainSim: the fly-off call
must receive the key choice; the unfixed list passes -1. Game bytes stay in tmp/.
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
                    sites=dict(store=0x31498, list=0x314b0, branch=0x276b0), trainsim=0x1827e, flyoff=0x17d06),
    'german': dict(path='tmp/game/WingCommanderCD32/data/wing.german',
                   sha='2047da69f2c83803675921afd86204747609a5c59dd3e7f67d954d785677dabe',
                   psygore=0x1cf4, fix='fix_patch_de', save=0x277a0, a4=0x7ffe,
                   app=-1288, prefix=-1284, name=-1252,
                   sites=dict(store=0x3165a, list=0x31672, branch=0x27872), trainsim=0x18338, flyoff=0x17db6),
}
SLAVE = 0x200000          # slave payload
RES = 0x280000            # resload jump table, each entry an RTS
DATA = 0x300000           # game A4 data area (A4 = DATA + 0x8000)
SLOTS = 0x320000          # 8 x 116-byte slot records
STRINGS = 0x330000
STACK = 0x3f0000
STOP = 0x3fff00
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
            else:
                f = self.string(self.reg(1))
            self.calls.append((name, f))
        self.cb = C.CFUNCTYPE(None, P, Q, C.c_uint32, P)(hook)
        handle = Z(); ck(u.uc_hook_add(self.h, C.byref(handle), 4, self.cb, None, RES, RES+255))

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


def save(cfg, code, blob, files, slot, name):
    m = Machine(code, blob, cfg, files)
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--sabotage', choices=('store-failure', 'list-stub'),
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
        assert fixlog == [(3, s['store']), (2, s['list']), (7, s['branch']), (7, cfg['trainsim'])], fixlog
        assert fixed[s['branch']:s['branch']+2] == bytes.fromhex('6604')
        # TrainSim: move.w d4,-(sp) -> move.w (a2),-(sp), before pea/jsr fly-off.
        t = cfg['trainsim']
        assert original[t:t+4] == bytes.fromhex('3f04486c') and original[t+6:t+8] == bytes.fromhex('4eba')
        assert fixed[t:t+2] == bytes.fromhex('3f12') and fixed[t+2:t+8] == original[t+2:t+8]
        changed = [i for i in range(len(psy)) if psy[i] != fixed[i]]
        assert all(any(x <= i < x+6 for x in s.values()) or t <= i < t+2
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
            assert set(files) == set(before) | {f'Bed_{slot}'}
            assert not any(c[0] in ('DeleteFile', 'unexpected') for c in calls), (case, calls)
            sizes = [c[1] for c in calls if c[0] == 'GetFileSize']
            assert sizes == [f'Bed_{n}' for n in range(8)]*2, sizes
            cases[case] = dict(result=r, files=sorted(files))
        # An emptied slot is deleted, as in Psygore's slave.
        files = {'Bed_2': b'\2'*116, 'Bed_4': b'\4'*116}
        r, after, calls = save(cfg, fixed, blob, files, 2, 0)
        assert 'Bed_2' not in files and files['Bed_4'] == b'\4'*116 and r == 1
        cases['delete'] = dict(result=r, files=sorted(files))
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
        report[lang] = cases
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(sha256=meta['sha256'], games=report), indent=2)+'\n')
    print(json.dumps(dict(pass_=True, sha256=meta['sha256'])))


if __name__ == '__main__':
    main()
