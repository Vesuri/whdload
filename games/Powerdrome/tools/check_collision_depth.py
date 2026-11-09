#!/usr/bin/env python3
"""Execute the enhanced track-collision depth test (timing_collision.s) with shared Unicorn.

Source ../../common/env.sh first. Requires vasm and AMIGA_UNICORN; no game bytes are used.
For random planes, previous positions and distances after a step, the hook at $ad5a must
report "not deep" (BGT taken) exactly when the distance before the step plus 18/4 of the
step's travel (the 32-bit difference of the two native distances) is above -819200,
keep every register, and never wrap the scaled depth.
"""
import ctypes as C
import os
from pathlib import Path
import random
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
out = root / 'tmp/collision-depth'
out.mkdir(parents=True, exist_ok=True)
(out/'harness.s').write_text(''' org $200000
 dc.l entry
; The native BGT.S, captured with SGT (Unicorn does not report lazily computed flags in SR).
entry
 bsr timing_collision_depth
 sgt $100000
 rts
timing_world20_test_control
 rts
 INCLUDE timing_collision.s
''')
subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin', '-I'+str(root/'src'),
                '-o', str(out/'harness.bin'), str(out/'harness.s')], check=True, stdout=subprocess.DEVNULL)

lib = C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
ptr, u64, sz = C.c_void_p, C.c_uint64, C.c_size_t
for n, signature in {'uc_open': [C.c_int, C.c_int, C.POINTER(ptr)], 'uc_mem_map': [ptr, u64, sz, C.c_uint],
                     'uc_mem_write': [ptr, u64, ptr, sz], 'uc_mem_read': [ptr, u64, ptr, sz], 'uc_reg_write': [ptr, C.c_int, ptr],
                     'uc_reg_read': [ptr, C.c_int, ptr], 'uc_emu_start': [ptr, u64, u64, u64, sz]}.items():
    getattr(lib, n).argtypes = signature
lib.uc_ctl.argtypes = [ptr, C.c_uint]


def ok(err):
    assert err == 0, f'Unicorn error {err}'


uc = ptr()
ok(lib.uc_open(7, 1 << 30, C.byref(uc)))
ok(lib.uc_ctl(uc, C.c_uint(7 | 1 << 26 | 1 << 30), C.c_int(2)))  # 68020
ok(lib.uc_mem_map(uc, 0, 0x400000, 7))


def write(addr, data): ok(lib.uc_mem_write(uc, addr, data, len(data)))


def reg(n, value=None):
    v = C.c_uint32(0 if value is None else value & 0xffffffff)
    if value is None:
        ok(lib.uc_reg_read(uc, n, C.byref(v)))
        return v.value
    ok(lib.uc_reg_write(uc, n, C.byref(v)))


D = [9 + i for i in range(8)]       # Unicorn M68K: D0-D7 9-16, A0-A7 1-8, PC 18
A = [1 + i for i in range(8)]
PC, END, BASE, PLANES, RESULT = 18, 0x300000, 0xa6e, 0x1000, 0x100000
blob = (out/'harness.bin').read_bytes()
entry = struct.unpack_from('>I', blob)[0]
write(0x200000, blob)
s32 = lambda x: (x + 2**31) % 2**32 - 2**31
rng = random.Random(1234)
counts = [0, 0]
for case in range(20000):
    index = rng.randrange(4)
    normal = [rng.randrange(-16384, 16385) for _ in range(3)]
    constant = rng.randrange(-2**30, 2**30)
    prev = [rng.randrange(-32768, 32768) for _ in range(3)]
    before = s32(sum(n*p for n, p in zip(normal, prev)) - constant)
    # Distances after the step near the threshold and across the whole long range.
    after = rng.choice([before + rng.randrange(-400000, 400000), rng.randrange(-2**31, 2**31),
                        before - rng.randrange(0, 2**31)])
    after = s32(after)
    planes = bytearray(40)
    struct.pack_into('>hhhi', planes, index*10, *normal, constant)
    write(PLANES, bytes(planes))
    write(BASE+0x186, struct.pack('>hhh', *prev))
    regs = [index, 0x11110001, 0x22220002, 0x33330003, after & 0xffffffff, 0x55550005, 0x66660006, 0x77770007]
    for r, v in zip(D, regs):
        reg(r, v)
    for r, v in zip(A, [PLANES, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, BASE]):
        reg(r, v)
    reg(A[7], 0x380000)
    write(0x380000, struct.pack('>I', END))
    ok(lib.uc_emu_start(uc, entry, END, 0, 10000))
    assert reg(PC) == END
    assert [reg(r) for r in D] == [v & 0xffffffff for v in regs], case
    assert [reg(r) for r in A[:7]] == [PLANES, 0x1111, 0x2222, 0x3333, 0x4444, 0x5555, BASE], case
    b = C.create_string_buffer(1)
    ok(lib.uc_mem_read(uc, RESULT, b, 1))
    gt = b.raw == b'\xff'
    # Native distances are 32-bit; the travel is their 32-bit difference, then exact.
    depth4 = before*4 + s32(after - before)*18
    expected = depth4 > -819200*4
    assert gt == expected, (case, before, after, depth4)
    counts[expected] += 1
print(f'{sum(counts)} plane/step cases: {counts[0]} deep, {counts[1]} not; registers kept, no wrap')
