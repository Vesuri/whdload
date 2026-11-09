#!/usr/bin/env python3
"""Execute the enhanced input layer's stick handling with shared Unicorn.

Source ../../common/env.sh first. Requires vasm and AMIGA_UNICORN; no game bytes are used.
Scenario: push the mouse forward, let native contact damping reduce the stick, press A
(native reset), then check the private stick the controls read. Also checks that queued
movement older than a reset is discarded and that no stick sum ever wraps.

--baseline REV runs the same scenario against timing_input.s from git revision REV, whose
producer queued differences of the raw counters; it reports instead of asserting.
"""
import argparse
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', metavar='REV')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
out = root / 'tmp/input-axes' / ('baseline' if args.baseline else 'current')
out.mkdir(parents=True, exist_ok=True)

if args.baseline:
    source = subprocess.run(['git', 'show', f'{args.baseline}:./src/timing_input.s'], cwd=root,
                            check=True, capture_output=True, text=True).stdout
    (out/'timing_input.s').write_text(source)
    include = str(out)
else:
    include = str(root/'src')
new = not args.baseline
names = ['timing_input_initialize', 'timing_input_sample', 'timing_input_for_control',
         'timing_input_write_axes', 'timing_input_read_axes', 'timing_input_after_write_axes',
         'timing_input_after_read_axes', 'timing_input_clock', 'timing_input_x', 'timing_input_y',
         'timing_input_overflow', 'timing_state']
if new:
    names += ['timing_input_mouse_x', 'timing_input_mouse_y', 'timing_input_zero_axes']
harness = ' org $200000\n dc.l ' + ','.join(names) + '\n'
harness += '''TIMING_WORLD20 = 0
perf_game dc.l 0
timing_brake_joystick
 rts
timing_state
timing_last dc.l 0
 INCLUDE timing_input.s
'''
(out/'harness.s').write_text(harness)
subprocess.run([os.environ.get('VASM', 'vasmm68k_mot'), '-m68020', '-devpac', '-Fbin', '-I'+include,
                '-o', str(out/'harness.bin'), str(out/'harness.s')], check=True, stdout=subprocess.DEVNULL)

lib = C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
ptr, u64, sz = C.c_void_p, C.c_uint64, C.c_size_t
for n, signature in {'uc_open': [C.c_int, C.c_int, C.POINTER(ptr)], 'uc_mem_map': [ptr, u64, sz, C.c_uint],
                     'uc_mem_write': [ptr, u64, ptr, sz], 'uc_mem_read': [ptr, u64, ptr, sz],
                     'uc_reg_write': [ptr, C.c_int, ptr], 'uc_reg_read': [ptr, C.c_int, ptr],
                     'uc_emu_start': [ptr, u64, u64, u64, sz]}.items():
    getattr(lib, n).argtypes = signature
lib.uc_ctl.argtypes = [ptr, C.c_uint]


def ok(err):
    assert err == 0, f'Unicorn error {err}'


uc = ptr()
ok(lib.uc_open(7, 1 << 30, C.byref(uc)))
ok(lib.uc_ctl(uc, C.c_uint(7 | 1 << 26 | 1 << 30), C.c_int(2)))  # 68020
ok(lib.uc_mem_map(uc, 0, 0x400000, 7))
ok(lib.uc_mem_map(uc, 0xdff000, 0x1000, 7))


def write(addr, data): ok(lib.uc_mem_write(uc, addr, data, len(data)))


def read(addr, n):
    b = C.create_string_buffer(n)
    ok(lib.uc_mem_read(uc, addr, b, n))
    return b.raw


def word(addr, value=None):
    if value is None:
        return struct.unpack('>h', read(addr, 2))[0]
    write(addr, struct.pack('>H', value & 65535))


def reg(n, value=None):
    v = C.c_uint32(0 if value is None else value & 0xffffffff)
    if value is None:
        ok(lib.uc_reg_read(uc, n, C.byref(v)))
        return v.value
    ok(lib.uc_reg_write(uc, n, C.byref(v)))


A1, A6, D0, D1, D2, D3, SP, PC = 2, 7, 9, 10, 11, 12, 8, 18  # Unicorn M68K: A0-A7 1-8, D0-D7 9-16
END = 0x300000


def call(name, **regs):
    for r, v in regs.items():
        reg({'a1': A1, 'd0': D0, 'd1': D1, 'd2': D2, 'd3': D3}[r], v)
    reg(A6, BASE)
    reg(SP, 0x380000)
    write(0x380000, struct.pack('>I', END))
    ok(lib.uc_emu_start(uc, syms[name], END, 0, 200000))
    assert reg(PC) == END, (name, hex(reg(PC)))


blob = (out/'harness.bin').read_bytes()
syms = dict(zip(names, struct.unpack_from('>'+str(len(names))+'I', blob)))
write(0x200000, blob)
for stub in ('timing_input_after_write_axes', 'timing_input_after_read_axes'):
    write(syms[stub]+2, struct.pack('>I', END))
BASE = 0xa6e
word(0xdff01c, 0x4000)        # INTENAR: master enable set
RAW_X, RAW_Y, FIELDS = BASE+0x42a, BASE+0x42e, 0x48fe
field = 0


def vbl(dx=0, dy=0):
    """One native VBL: mouse accumulation (hooked, or the native ADD.W), then the producer."""
    global field
    if new:
        if dx:
            call('timing_input_mouse_x', d0=dx & 0xff, d1=0)
        if dy:
            call('timing_input_mouse_y', d1=dy & 0xff)
    else:
        word(RAW_X, word(RAW_X)+dx)
        word(RAW_Y, word(RAW_Y)+dy)
    field += 1
    write(FIELDS, struct.pack('>I', field))
    call('timing_input_sample', a1=syms['timing_state'], d0=0)


def control():
    write(syms['timing_input_clock'], struct.pack('>I', field*4+1000))
    call('timing_input_for_control')
    return word(syms['timing_input_x']), word(syms['timing_input_y'])


def damp(times):
    """Native contact damping at $d05e: axis*230/256 written back through $d082."""
    for _ in range(times):
        x, y = control()
        call('timing_input_write_axes', d2=(x*230) >> 8, d3=(y*230) >> 8)


def native_reset():
    if new:
        call('timing_input_zero_axes')
    else:
        word(RAW_X, 0)
        word(RAW_Y, 0)


call('timing_input_initialize', a1=syms['timing_state'], d3=0)
for _ in range(40):
    vbl(dy=-125)                      # mouse forward: nose down
pushed = control()
damp(40)                              # scraping the floor
damped = control()
native_reset()                        # A: reposition in the centre of the track
vbl()
after = control()
print(f'pushed {pushed}, damped {damped}, after A {after}')
if args.baseline:
    print('baseline: the private stick after A is', 'reversed' if after[1] > 0 else 'not reversed')
    raise SystemExit
assert pushed == (0, -5000), pushed
assert abs(damped[1]) < 100, damped
assert after == (0, 0), f'A must recentre the stick, got {after}'
assert (word(RAW_X), word(RAW_Y)) == (0, 0)

vbl(dy=10)
assert control() == (0, 10), 'movement after a reset is kept'
for _ in range(3):
    vbl(dx=20, dy=20)                 # queued, not yet consumed by a control epoch
native_reset()
vbl()
assert control() == (0, 0), 'movement older than the reset is discarded'

for n in range(400):
    vbl(dx=127, dy=-127)              # 50,800 counts each way: would wrap a word
    if n % 4 == 3:
        control()                     # the game consumes about every 4.5 fields
sat = control()
assert sat == (32767, -32767) and (word(RAW_X), word(RAW_Y)) == (32767, -32767), sat
vbl(dx=-127, dy=127)
assert control() == (32640, -32640), 'pulling back responds at once'
assert struct.unpack('>I', read(syms['timing_input_overflow'], 4))[0] == 0
print('A recentres the damped stick; older queued movement is discarded; stick sums saturate at +-32767')
