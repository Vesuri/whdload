#!/usr/bin/env python3
"""What each main-loop call writes: a frame's calls replayed in Unicorn from a chip dump.

    python3 tools/callwrites.py capture OUT [FRAME]   chip $0-$87fff at the main loop's top
    python3 tools/callwrites.py writes DUMP           per call, the bytes it changed, by area
    python3 tools/callwrites.py split DUMP [PASSES]   drawing skipped on alternate passes:
                                                      the game state still the same?
    python3 tools/callwrites.py compare DUMP A B      two tools/gametime.py captures, less
                                                      what drawing writes (from DUMP)
    python3 tools/callwrites.py who DUMP LO HI [PASSES]  which calls and PCs read and write
                                                      $LO-$HI (hex) over PASSES whole passes

`capture` needs a server booted with tools/boot.sh: it runs to the demo's start, then to the
main loop's top ($64204) with the frame counter $c9f4 at FRAME (default 200), and dumps all
544 KB of chip memory. `writes` runs the loop's calls in order on Unicorn's 68000 from that
state (the custom chips and CIAs are plain memory, no interrupts run, the clear flag $606ac
reads 0 so the renderer does not wait) and lists, per call, the changed bytes in the
work memory ($1000-$3b7ff), the image ($3b800-$687ff) and the display buffers.

`split` runs PASSES main-loop passes (default 8) twice from the dump: every pass whole, and
with the drawing calls (the renderer, the swap, the clear request: DRAW) left out of every
other pass, the last pass whole in both. Both runs then differ only where the left-out
drawing would have written, if the drawing writes no game state. It lists the bytes that
differ in the work memory and the image, the stack below $4b546 left out.

`compare` lists the bytes that differ between two captures of the same tick (tools/
gametime.py: work memory and image) outside what is not game state: every byte the drawing
calls write in 10 passes from DUMP, the renderer's object transforms ($1100-$11ff, which
nothing else reads or writes), the depth lists' storage ($16ac-$a36f), the radar list
($9ea6-$a2a5), the stack, the polygon filler's edge state ($67d86-$67d8d), the clear
request ($606a6-$606b3), the VBL's sound countdowns ($58480-$584cf) and the slave's
patches (in the original or Enhanced). What is left is game state.
"""
import ctypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UC_ARCH_M68K, UC_MODE_BIG_ENDIAN = 7, 1 << 30
UC_CTL_CPU_MODEL, UC_CPU_M68K_M68000 = 7, 0
REG_A0, REG_D0, REG_SR, REG_PC = 1, 9, 17, 18
CHIP = 0x88000
SENTINEL = 0xF00000
STACK = 0x4b546
CALLS = [0x672fc, 0x60a1c, 0x66718, 0x6249a, 0x65174, 0x64d74, 0x61f32, 0x58d8c, 0x58cfe,
         0x65a78, 0x64356]


def load_unicorn():
    lib = Path(os.environ.get('AMIGA_UNICORN', Path.home() / '.local/share/amiga/unicorn'))
    uc = ctypes.CDLL(str(lib / 'lib/libunicorn.2.dylib'))
    uc.uc_reg_write.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    uc.uc_reg_read.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
    uc.uc_mem_write.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_char_p, ctypes.c_size_t]
    uc.uc_mem_read.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_size_t]
    uc.uc_mem_map.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_size_t, ctypes.c_uint32]
    uc.uc_emu_start.argtypes = [ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64,
                                ctypes.c_uint64, ctypes.c_size_t]
    uc.uc_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int]
    return uc


class Machine:
    def __init__(self, chip, cpu=UC_CPU_M68K_M68000):
        self.uc = uc = load_unicorn()
        h = ctypes.c_void_p()
        assert uc.uc_open(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, ctypes.byref(h)) == 0
        self.h = h
        assert uc.uc_ctl(h, UC_CTL_CPU_MODEL | (1 << 26) | (1 << 30), ctypes.c_int(cpu)) == 0
        for base, size in ((0, 0x100000), (0xbf0000, 0x10000), (0xdf0000, 0x10000),
                           (SENTINEL, 0x1000)):
            assert uc.uc_mem_map(h, base, size, 7) == 0
        self.write(0, chip)

    def write(self, addr, data):
        assert self.uc.uc_mem_write(self.h, addr, bytes(data), len(data)) == 0

    def read(self, addr, n):
        buf = ctypes.create_string_buffer(n)
        assert self.uc.uc_mem_read(self.h, addr, buf, n) == 0
        return buf.raw

    def reg(self, r, v=None):
        x = ctypes.c_uint32(v if v is not None else 0)
        if v is None:
            self.uc.uc_reg_read(self.h, r, ctypes.byref(x))
            return x.value
        self.uc.uc_reg_write(self.h, r, ctypes.byref(x))

    def call(self, pc, limit=20_000_000):
        self.write(0x606ac, b'\0\0')
        self.reg(REG_SR, 0x2700)
        sp = STACK - 4
        self.write(sp, SENTINEL.to_bytes(4, 'big'))
        self.reg(REG_A0 + 7, sp)
        err = self.uc.uc_emu_start(self.h, pc, SENTINEL, 0, limit)
        if err or self.reg(REG_PC) != SENTINEL:
            raise RuntimeError(f'emulation error {err} at pc {self.reg(REG_PC):#x} from {pc:#x}')


DRAW = (0x65174, 0x58d8c, 0x58cfe)


def passes(m, n, skip):
    for k in range(n):
        c = int.from_bytes(m.read(0xc9f4, 2), 'big')
        m.write(0xc9f4, ((c + 1) & 0xffff).to_bytes(2, 'big'))
        for pc in CALLS:
            if skip(k) and pc in DRAW:
                continue
            m.call(pc)


HOOKMEM = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_int, ctypes.c_uint64, ctypes.c_int,
                           ctypes.c_int64, ctypes.c_void_p)


def who(dump, lo, hi, n):
    import collections
    m = Machine(Path(dump).read_bytes()[:CHIP])
    seen = collections.Counter()
    cur = [0]

    def cb(uc, typ, addr, size, value, user):
        pc = ctypes.c_uint32()
        m.uc.uc_reg_read(m.h, REG_PC, ctypes.byref(pc))
        seen[(cur[0], 'w' if typ == 17 else 'r', pc.value)] += 1

    hook = HOOKMEM(cb)
    hh = ctypes.c_size_t()
    m.uc.uc_hook_add.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_int,
                                 ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
    assert m.uc.uc_hook_add(m.h, ctypes.byref(hh), (1 << 10) | (1 << 11),
                            ctypes.cast(hook, ctypes.c_void_p), None, lo, hi - 1) == 0
    for _ in range(n):
        for pc in CALLS:
            cur[0] = pc
            m.call(pc)
    for (call, rw, pc), k in sorted(seen.items()):
        print(f'call ${call:05x} {rw} pc ${pc:05x} x{k}')


PATCHED = ((0x607fe, 0x60804), (0x608c0, 0x608c8), (0x641fe, 0x64204), (0x64212, 0x6421a), (0x644b6, 0x644c0),
           (0x65d30, 0x65d36), (0x65d84, 0x65d8c), (0x67116, 0x6711e))
NOT_STATE = ((0x1100, 0x1200), (0x16ac, 0xa370), (0x4b000, 0x4b546), (0x67d86, 0x67d8e), (0x606a6, 0x606b4),
             (0x58480, 0x584d0)) + PATCHED


def compare(dump, a, b):
    m = Machine(Path(dump).read_bytes()[:CHIP])
    mask = bytearray(CHIP)
    drawing = [False]

    def cb(uc, typ, addr, size, value, user):
        if drawing[0]:
            mask[addr:addr + size] = b'\1' * size

    hook = HOOKMEM(cb)
    hh = ctypes.c_size_t()
    m.uc.uc_hook_add.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t), ctypes.c_int,
                                 ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint64, ctypes.c_uint64]
    assert m.uc.uc_hook_add(m.h, ctypes.byref(hh), 1 << 11, ctypes.cast(hook, ctypes.c_void_p),
                            None, 0x1000, 0x6ffff) == 0
    for _ in range(10):
        for pc in CALLS:
            drawing[0] = pc in DRAW
            m.call(pc)
    for lo, hi in NOT_STATE:
        mask[lo:hi] = b'\1' * (hi - lo)
    ra = Path(a).read_bytes() + Path(a + '.img').read_bytes()
    rb = Path(b).read_bytes() + Path(b + '.img').read_bytes()
    diff = [0x1000 + i for i in range(len(ra)) if ra[i] != rb[i] and not mask[0x1000 + i]]
    # B with its code in fast memory (tools/codebase.py): its code pointers differ from A's by
    # one distance. Bytes of an even long that is a code-area address in A and that plus the
    # distance in B are the same state.
    def long(r, x):
        return int.from_bytes(r[x - 0x1000:x - 0x1000 + 4], 'big')
    moved, cands = set(), {}
    for x in diff:
        for y in (x & ~1, (x & ~1) - 2):
            va, vb = long(ra, y), long(rb, y)
            if 0x57000 <= va < 0x68800 and vb != va:
                cands[vb - va] = cands.get(vb - va, 0) + 1
    if cands:
        d = max(cands, key=cands.get)
        for x in diff:
            for y in (x & ~1, (x & ~1) - 2):
                va, vb = long(ra, y), long(rb, y)
                if 0x57000 <= va < 0x68800 and vb - va == d:
                    moved.add(x)
        longs = {x & ~1 if long(rb, x & ~1) - long(ra, x & ~1) == d else (x & ~1) - 2 for x in moved}
        print(f'code pointers moved by ${d:x}: {len(longs)} longs')
        diff = [x for x in diff if x not in moved]
    print(f'game state: {len(diff)} bytes differ: ' + ' '.join(f'${x:05x}' for x in diff[:60]))


def split(dump, n):
    chip = Path(dump).read_bytes()[:CHIP]
    a, b = Machine(chip), Machine(chip)
    passes(a, n, lambda k: False)
    passes(b, n, lambda k: k % 2 == 0 and k < n - 1)
    ra, rb = a.read(0, CHIP), b.read(0, CHIP)
    for lo, hi, name in AREAS[:3]:
        r = [(s, k) for s, k in runs(ra[lo:hi], rb[lo:hi], lo) if not 0x4b000 <= s < 0x4b546]
        print(f'{name}: {sum(k for _, k in r)} bytes in {len(r)} runs: '
              + ' '.join(f'${s:05x}+{k}' for s, k in r[:60]))


AREAS = ((0x1000, 0x3b800, 'work'), (0x3b800, 0x68800, 'image'), (0x68800, 0x70000, 'image+'),
         (0x70000, 0x78000, 'display $70000'), (0x78000, 0x80000, 'display $78000'),
         (0x80000, 0x88000, 'above 512K'), (0, 0x1000, 'low'))


def runs(a, b, base):
    out, i = [], 0
    while i < len(a):
        if a[i] != b[i]:
            j = i
            while j < len(a) and (a[j] != b[j] or (j + 1 < len(a) and a[j + 1] != b[j + 1])):
                j += 1
            out.append((base + i, j - i))
            i = j
        else:
            i += 1
    return out


def writes(dump):
    m = Machine(Path(dump).read_bytes()[:CHIP])
    for pc in CALLS:
        before = m.read(0, CHIP)
        m.call(pc)
        after = m.read(0, CHIP)
        print(f'${pc:05x} (Disk.1 +{pc - 0x3b800:05x})')
        for lo, hi, name in AREAS:
            r = runs(before[lo:hi], after[lo:hi], lo)
            if not r:
                continue
            n = sum(k for _, k in r)
            shown = ' '.join(f'${s:05x}+{k}' for s, k in r[:40])
            print(f'  {name}: {n} bytes in {len(r)} runs: {shown}{" ..." if len(r) > 40 else ""}')


def capture(out, frame):
    sys.path.insert(0, str(ROOT.parents[1] / 'common/tools'))
    from game_server import game_server
    srv = game_server('virus')
    out = Path(out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    srv.request('until 0x641fe')
    srv.request(f'gdb break *0x64204 if *(unsigned short *)0xc9f4 == {frame - 1}')
    srv.request('gdb continue')
    srv.request('gdb delete')
    srv.request(f'gdb dump binary memory {out} 0 {CHIP:#x}')
    print(f'dumped chip at the main loop top, frame {frame}: {out}')


if __name__ == '__main__':
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == 'capture':
        capture(a[1], int(a[2]) if len(a) > 2 else 200)
    elif len(a) >= 2 and a[0] == 'split':
        split(a[1], int(a[2]) if len(a) > 2 else 8)
    elif len(a) == 4 and a[0] == 'compare':
        compare(a[1], a[2], a[3])
    elif len(a) >= 4 and a[0] == 'who':
        who(a[1], int(a[2], 16), int(a[3], 16), int(a[4]) if len(a) > 4 else 2)
    elif len(a) == 2 and a[0] == 'writes':
        writes(a[1])
    else:
        sys.exit(__doc__)
