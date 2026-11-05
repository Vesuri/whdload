#!/usr/bin/env python3
"""Execute the actual mouse assembly with shared Unicorn; proprietary inputs stay local.

Source amiga/env.sh first. Requires vasm and AMIGA_UNICORN. This is an arithmetic
and native-matrix integration check, not a substitute for in-game input captures.
"""
import argparse
import ctypes as C
import math
import os
from pathlib import Path
import struct
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--ticks',type=int,default=500)
args=parser.parse_args()
assert args.ticks>=500
root = Path(__file__).resolve().parents[1]
out = root / 'tmp/mouse-steering/math'
out.mkdir(parents=True, exist_ok=True)
names = ['timing_mouse_trig', 'timing_mouse_gain', 'timing_mouse_divide',
         'timing_mouse_rotate', 'timing_mouse_finish', 'timing_mouse_reset',
         'timing_mouse_state', 'timing_mouse_angles', 'timing_mouse_rates',
         'timing_mouse_native_trig', 'timing_mouse_native_pitch',
         'timing_mouse_native_yaw', 'timing_mouse_native_roll',
         'timing_mouse_after_rotate', 'timing_mouse_candidate',
         'timing_input_mode', 'test_due']
subprocess.run(['python3', str(root/'tools/mouse_sine.py'), str(root/'tmp/build/mouse-sine.i')], check=True)
source = ' org $200000\n dc.l ' + ','.join(names) + '\n'
source += ''' INCLUDE timing_mouse.s
timing_mouse_sine
 INCLUDE ../tmp/build/mouse-sine.i
perf_game dc.l 0
timing_input_mode dc.w 0
test_due dc.w 1
timing_world20_test_control
 move.w test_due(pc),d0
 rts
timing_orientation_move
 rts
'''
(out/'harness.s').write_text(source)
subprocess.run([os.environ.get('VASM', str(Path.home()/'.local/vasmm68k_mot')),
                '-m68000', '-devpac', '-Fbin', '-I'+str(root/'whdload'),
                '-o', str(out/'harness.bin'), str(out/'harness.s')], check=True,
               stdout=subprocess.DEVNULL)
lib = C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
ptr = C.c_void_p
u64 = C.c_uint64
u32 = C.c_uint32
sz = C.c_size_t
for n, signature in {'uc_open':[C.c_int,C.c_int,C.POINTER(ptr)],
                'uc_mem_map':[ptr,u64,sz,C.c_uint],
                'uc_mem_write':[ptr,u64,ptr,sz],
                'uc_mem_read':[ptr,u64,ptr,sz],
                'uc_reg_write':[ptr,C.c_int,ptr],
                'uc_reg_read':[ptr,C.c_int,ptr],
                'uc_emu_start':[ptr,u64,u64,u64,sz]}.items():
    getattr(lib,n).argtypes=signature

def ok(err):
    assert err == 0, f'Unicorn error {err}'

lib.uc_ctl.argtypes=[ptr,C.c_uint]
uc=ptr()
ok(lib.uc_open(7,1<<30,C.byref(uc)))
# UC_CTL_WRITE(UC_CTL_CPU_MODEL,1), UC_CPU_M68K_M68020.
ok(lib.uc_ctl(uc,C.c_uint(7 | 1<<26 | 1<<30),C.c_int(2)))
ok(lib.uc_mem_map(uc,0,0x400000,7))

def write(addr,data):
    ok(lib.uc_mem_write(uc,addr,data,len(data)))

def read(addr,n):
    b=C.create_string_buffer(n)
    ok(lib.uc_mem_read(uc,addr,b,n))
    return b.raw

def word(addr,value): write(addr,struct.pack('>H',value&65535))
def reg(n,value=None):
    v=u32(value or 0)
    if value is None:
        ok(lib.uc_reg_read(uc,n,C.byref(v)))
        return v.value
    ok(lib.uc_reg_write(uc,n,C.byref(v)))

def call(name,end=0x300000):
    reg(8,0x380000)
    write(0x380000,struct.pack('>I',end))
    ok(lib.uc_emu_start(uc,syms[name],end,0,20000))
    assert reg(18)==end, (name,hex(reg(18)))

blob=(out/'harness.bin').read_bytes()
syms=dict(zip(names,struct.unpack_from('>'+str(len(names))+'I',blob)))
write(0x200000,blob)
pd=(root/'tmp/extracted/pd').read_bytes()[32:]
write(0,pd[:0x18548])
for label,address in [('trig',0x8d0e),('pitch',0xaa4c),('yaw',0xab00),('roll',0xabba)]:
    write(syms['timing_mouse_native_'+label]+2,struct.pack('>I',address))
write(syms['timing_mouse_after_rotate']+2,struct.pack('>I',0x300000))
reg(7,0xa6e)
reg(17,0)

# The unmodified native lookup remains available for native rotation paths.
table=struct.unpack_from('>360h',pd,0x2948)
for angle in range(360):
    reg(9,angle)
    call('timing_mouse_native_trig')
    assert (C.c_int16(reg(10)).value,C.c_int16(reg(11)).value)==(table[angle],table[(angle+90)%360])
# Every Q12 angle in a full turn, both signs, against mathematical trigonometry.
max_error=0
for angle in range(-360*4096,360*4096):
    reg(9,angle&0xffffffff)
    call('timing_mouse_trig')
    sine,cosine=(C.c_int32(reg(r)).value for r in (10,11))
    theta=math.radians(angle/4096)
    max_error=max(max_error,abs(sine-(1<<30)*math.sin(theta)),abs(cosine-(1<<30)*math.cos(theta)))
# Interpolation curvature bound M*h^2/8, plus table and interpolation rounding.
bound=(1<<30)*math.radians(1/64)**2/8+1
assert max_error <= bound,max_error
print(f'2,949,120 signed fractional angles; max Q30 trig error {max_error:.3f}')

# Preserve all of the mouse gain, including counts native integer division lost.
state=syms['timing_mouse_state']
for denominator in (1,2,3,7,16,31,38,55):
    word(0xa6e+0x1ec,denominator)
    word(0xa6e+0x1ee,denominator)
    for delta in range(-128,129):
        reg(11,delta&65535);reg(12,delta&65535)
        call('timing_mouse_gain')
        reg(11,(-C.c_int16(reg(11)).value)&65535)
        call('timing_mouse_divide')
        frac=struct.unpack('>hh',read(state+10,4))
        got=(C.c_int16(reg(9)).value*4096+frac[0],C.c_int16(reg(10)).value*4096+frac[1])
        expected=(delta*2176/denominator,-delta*2176/denominator)
        assert all(abs(x-y)<1.01 for x,y in zip(got,expected)),(denominator,delta,got,expected)
print('2,056 signed mouse inputs/calibrations retain sensitivity to within 1/4096 degree per control epoch')

# Run the real native matrix bodies with one held sub-degree yaw. Recompute
# the epoch from its base on every fine step, as the game does. Compare the
# accumulated heading and matrix lengths against a continuous rotation oracle.
for rate in (-2048,2048,-4096,4096,-39,39):
    call('timing_mouse_reset')
    identity=struct.pack('>9h',16384,0,0,0,16384,0,0,0,16384)
    write(0xa6e+0x3e8,identity)
    word(0xa6e+0x258,0)
    word(0xa6e+0x3a6,0);word(0xa6e+0x3a8,0);word(0xa6e+0x3aa,0)
    word(state+12,rate)
    next_control=0
    previous=identity
    changed=0
    for tick in range(args.ticks):
        due=tick*4>=next_control
        word(syms['test_due'],int(due))
        if due: next_control+=18
        call('timing_mouse_rotate')
        candidate=read(0xa6e+0x3fa,18)
        changed += candidate!=previous
        previous=candidate
        write(0xa6e+0x3e8,candidate)
        call('timing_mouse_finish')
    matrix=struct.unpack('>9h',previous)
    heading=math.degrees(math.atan2(matrix[6],matrix[0]))
    expected=-rate/4096*args.ticks*20/90
    error=(heading-expected+180)%360-180
    # Native yaw sign is determined by its row rotation convention.
    assert abs(error)<0.01,(rate,heading,expected,error)
    norms=[math.sqrt(sum(matrix[r*3+c]**2 for c in range(3)))/16384 for r in range(3)]
    assert max(abs(n-1) for n in norms)<0.001,(rate,norms)
    assert changed >= (args.ticks//3 if abs(rate)<64 else args.ticks), (rate,changed)
    print(f'{rate/4096:+.6f} degree/90 ms: {changed}/{args.ticks} steps move; heading error {error:+.3f} degrees; row lengths {norms}')

# Rejection, native writers, joystick fallback and fresh-session reset.
def initialize_yaw(rate):
    call('timing_mouse_reset')
    write(0xa6e+0x3e8,identity)
    word(syms['timing_input_mode'],0)
    word(0xa6e+0x258,0)
    for off in (0x3a6,0x3a8,0x3aa): word(0xa6e+off,0)
    word(state+12,rate)
    word(syms['test_due'],1)

initialize_yaw(2048)
call('timing_mouse_rotate')
first=read(0xa6e+0x3fa,18)
# Native rejects: leave committed identity instead of copying the candidate.
call('timing_mouse_finish')
assert read(state+4,2)==b'\0\0'
word(syms['test_due'],0)
call('timing_mouse_rotate')
assert read(0xa6e+0x3fa,18)==first,'Rejected rotation leaked into the next step'
write(0xa6e+0x3e8,first)
call('timing_mouse_finish')
call('timing_mouse_rotate')
write(0xa6e+0x3e8,read(0xa6e+0x3fa,18))
call('timing_mouse_finish')
# A native matrix writer (reset/incident) outside our candidate path.
write(0xa6e+0x3e8,identity)
call('timing_mouse_rotate')
assert read(0xa6e+0x3fa,18)==first,'Native matrix replacement retained stale fractional orientation'
# Joystick falls through to precisely the original matrix bodies.
word(syms['timing_input_mode'],1)
for off,value in ((0x3a6,3),(0x3a8,-2),(0x3aa,1)): word(0xa6e+off,value)
write(0xa6e+0x3fa,identity)
call('timing_mouse_rotate')
actual=read(0xa6e+0x3fa,18)
assert read(state+132,12)==bytes(12), 'Mode switch retained angle remainders'
write(0xa6e+0x3fa,identity)
for axis in ('roll','yaw','pitch'): call('timing_mouse_native_'+axis)
assert read(0xa6e+0x3fa,18)==actual
call('timing_mouse_reset')
assert read(state,144)==bytes(144)
print('Rejected candidates, external matrix resets, joystick fallback and session reset pass')
