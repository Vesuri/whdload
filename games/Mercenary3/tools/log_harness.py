#!/usr/bin/env python3
"""Check F4's log conversion against the original, for every input, under shared Unicorn.

  . ../../common/env.sh; python3 tools/log_harness.py [--quick]

Assembles a 68020 driver with the original Disk.1 $4EDE4..$4EF91 twice: one copy as
shipped, one patched as _hotcode patches M1's copy with src/log-f4.i. Both run in
the emulator for each input and the driver compares d1, d6, d7 and the condition codes
(X included). The scratch registers' starting values and flags vary with the input.
Entries and inputs: $4EE88 every 32-bit value, $4EE84 every 28-bit value, $4EE76 every
word with varied high words. --quick tests 1/257 of each range (spread). Exits non-zero
on the first difference. The game is read from GAME_DRAWER (default tmp/game/...).
"""
import argparse
import ctypes as C
import multiprocessing
import os
from pathlib import Path
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GAME = Path(os.environ.get('GAME_DRAWER', ROOT / 'tmp/game/Mercenary3_v1.2_0356/Mercenary3'))
OUT = ROOT / 'tmp/log-harness'
BASE, STACK, RESULT = 0x1000, 0x80000, 0x7f000

DRIVER = r'''
	org	$1000
	bra.w	start
	dc.l	done
; In: a2 = entry offset in the block, d5 = first input, a5 = end (exclusive, wraps),
; d4 = step. Out at done: d2 = 0 passed, else 1 with d5 = the input.
start	lea	f4code(pc),a0
	lea	new+$4ee88-$4ede4(pc),a1
	move.w	#(_f4end-_f4code)/2-1,d0
.copy	move.w	(a0)+,(a1)+
	dbra	d0,.copy
	move.b	#_f4word-_f4code+4,new+$4ee83-$4ede4
	lea	$7f000,a6
	lea	orig(pc),a3
	adda.l	a2,a3
	lea	new(pc),a4
	adda.l	a2,a4
loop	bsr.b	setup
	jsr	(a3)
	move.w	ccr,d0
	movem.l	d0-d1/d6-d7,(a6)
	bsr.b	setup
	jsr	(a4)
	move.w	ccr,d0
	moveq	#1,d2
	cmp.l	(a6),d0
	bne.b	done
	cmp.l	4(a6),d1
	bne.b	done
	cmp.l	8(a6),d6
	bne.b	done
	cmp.l	12(a6),d7
	bne.b	done
	add.l	d4,d5
	cmpa.l	d5,a5
	bne.b	loop
	moveq	#0,d2
done	nop
	stop	#$2700

setup	move.l	d5,d1
	move.l	d5,d6
	not.l	d6
	move.l	d5,d7
	ror.l	#7,d7
	eori.l	#$5a3c96e1,d7
	move.l	d5,d0
	lsr.l	#3,d0
	eor.l	d5,d0
	andi.w	#$1f,d0
	move.w	d0,ccr
	rts

orig
{block}
new
{block}
	cnop	0,4
f4code
	include	"log-f4.i"
'''

# (name, entry offset, first, end exclusive, step, input transform note)
CASES = [('$4EE76 word', 0x4ee76, 0, 1 << 24, 1),
         ('$4EE84 28-bit', 0x4ee84, 0, 1 << 28, 1),
         ('$4EE88 32-bit', 0x4ee88, 0, 1 << 32, 1)]


def build():
    OUT.mkdir(parents=True, exist_ok=True)
    disk = GAME / 'Disk.1'
    if not disk.is_file():
        sys.exit(f'log_harness: {disk} missing (extract the game into tmp/ first)')
    code = disk.read_bytes()[0x4ede4:0x4ef92]
    block = '\n'.join('\tdc.b\t' + ','.join(f'${b:02x}' for b in code[i:i + 16])
                      for i in range(0, len(code), 16))
    (OUT / 'driver.s').write_text(DRIVER.replace('{block}', block))
    vasm = os.environ.get('VASM', str(Path.home() / '.local/vasmm68k_mot'))
    subprocess.run([vasm, '-quiet', '-m68020', '-devpac', '-Fbin',
                    '-I' + str(ROOT / 'src'), '-o', str(OUT / 'driver.bin'), str(OUT / 'driver.s')],
                   check=True, stdout=subprocess.DEVNULL)
    blob = (OUT / 'driver.bin').read_bytes()
    return blob, struct.unpack_from('>I', blob, 4)[0]


def run(job):
    blob, done, entry, first, end, step = job
    lib = C.CDLL(str(Path(os.environ.get('AMIGA_UNICORN', Path.home() / '.local/share/amiga/unicorn'))
                     / 'lib/libunicorn.2.dylib'))
    ptr, u64, sz = C.c_void_p, C.c_uint64, C.c_size_t
    lib.uc_open.argtypes = [C.c_int, C.c_int, C.POINTER(ptr)]
    lib.uc_mem_map.argtypes = [ptr, u64, sz, C.c_uint]
    lib.uc_mem_write.argtypes = [ptr, u64, ptr, sz]
    lib.uc_reg_write.argtypes = [ptr, C.c_int, ptr]
    lib.uc_reg_read.argtypes = [ptr, C.c_int, ptr]
    lib.uc_emu_start.argtypes = [ptr, u64, u64, u64, sz]
    lib.uc_ctl.argtypes = [ptr, C.c_uint]
    uc = ptr()
    assert lib.uc_open(7, 1 << 30, C.byref(uc)) == 0                    # M68K, big endian
    assert lib.uc_ctl(uc, C.c_uint(7 | 1 << 26 | 1 << 30), C.c_int(2)) == 0   # CPU model 68020
    assert lib.uc_mem_map(uc, 0, 0x100000, 7) == 0
    assert lib.uc_mem_write(uc, BASE, blob, len(blob)) == 0

    def reg(n, value=None):
        v = C.c_uint32(value or 0)
        if value is None:
            lib.uc_reg_read(uc, n, C.byref(v))
            return v.value
        lib.uc_reg_write(uc, n, C.byref(v))
    # Registers: A0..A7 = 1..8, D0..D7 = 9..16, SR 17, PC 18.
    reg(3, entry - 0x4ede4)
    reg(14, first)
    reg(6, end & 0xffffffff)
    reg(13, step)
    reg(17, 0x2700)                                                     # SR first: it selects A7
    reg(8, STACK)
    err = lib.uc_emu_start(uc, BASE, done, 0, 0)
    pc, d2, d5 = reg(18), reg(11), reg(14)
    if err or pc != done:
        return f'emulation stopped at {pc:#x} (error {err})'
    return None if d2 == 0 else f'differs for input {d5:#010x}'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quick', action='store_true')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    args = ap.parse_args()
    blob, done = build()
    failed = False
    with multiprocessing.Pool(args.jobs) as pool:
        for name, entry, first, end, step in CASES:
            # Interleave the range across jobs: job k tests first+k, +n, ... (n = step*parts).
            parts = 64
            stride = step * parts * (257 if args.quick else 1)
            count = (end - first) // stride
            jobs = [(blob, done, entry, first + k * step, first + k * step + count * stride, stride)
                    for k in range(parts)]
            t = time.time()
            errors = [e for e in pool.map(run, jobs) if e]
            tested = count * parts
            print(f'{name}: {tested:,} inputs, {"FAIL " + errors[0] if errors else "identical"} '
                  f'({time.time() - t:.0f} s)', flush=True)
            failed |= bool(errors)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
