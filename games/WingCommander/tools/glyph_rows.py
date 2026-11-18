#!/usr/bin/env python3
"""The game's glyph row loop under Unicorn: one row per nibble 0-15.

The text routine draws each row of a glyph a byte at a time, the byte's low
nibble as four chunky pixels with bit 3 leftmost, through a 16-entry jump table
(E:2fdd6 CD32 English, G:2ff98 German, O:3065c floppy). rows() runs that loop
from its row start (dispatch-6: movea.l (a3)+,a0 / adda.l a1,a0 / move.w d1,d5)
over a 4-pixel glyph of 16 rows, row n holding nibble n, and returns the
pixels each row drew. Code is the code hunk, unrelocated: the loop and its
table are PC-relative.
"""
import ctypes as C, os, struct
from pathlib import Path

P = C.c_void_p; I = C.c_int; Q = C.c_uint64; Z = C.c_size_t
u = C.CDLL(str(Path(os.environ['AMIGA_UNICORN'])/'lib/libunicorn.2.dylib'))
for name, args in {'uc_open': [I, I, C.POINTER(P)], 'uc_ctl': [P, C.c_uint32], 'uc_mem_map': [P, Q, Q, C.c_uint32],
                   'uc_mem_write': [P, Q, P, Z], 'uc_mem_read': [P, Q, P, Z], 'uc_reg_write': [P, I, P],
                   'uc_reg_read': [P, I, P], 'uc_emu_start': [P, Q, Q, Q, Z], 'uc_close': [P]}.items():
    getattr(u, name).argtypes = args; getattr(u, name).restype = I
u.uc_strerror.argtypes = [I]; u.uc_strerror.restype = C.c_char_p

ROW_START = bytes.fromhex('205bd1c93a01')
DISPATCH = bytes.fromhex('101ad000343b00064efb2002')
BYTES, TABLE, ROWS, STACK, STOP = 0x100000, 0x100100, 0x101000, 0x102000, 0x103000
STRIDE, INK, PAPER = 16, 0xc5, 0x00


def ck(e):
    if e: raise RuntimeError(u.uc_strerror(e).decode())


def rows(code, dispatch):
    """The four pixels (True = ink) each nibble's row drew."""
    assert code[dispatch-6:dispatch] == ROW_START and code[dispatch:dispatch+12] == DISPATCH, 'not the glyph row loop'
    h = P(); ck(u.uc_open(7, 1 << 30, C.byref(h)))
    try:
        ck(u.uc_ctl(h, 7 | (1 << 26) | (1 << 30), I(2)))     # 68020
        ck(u.uc_mem_map(h, 0, 0x104000, 7))

        def write(a, b): ck(u.uc_mem_write(h, a, b, len(b)))

        def reg(r, v): x = C.c_uint32(v & 0xffffffff); ck(u.uc_reg_write(h, r, C.byref(x)))
        write(0, bytes(code))
        write(BYTES, bytes(range(16)))
        write(TABLE, b''.join(struct.pack('>I', ROWS+n*STRIDE) for n in range(16)))
        write(ROWS, bytes([PAPER])*(16*STRIDE))
        write(STACK, b'\0'*24+struct.pack('>I', STOP))       # movem.l (sp)+,d2-d5/a2-a3; rts
        write(STOP, b'\x4e\x71')
        reg(17, 0x2700)                  # SR first: writing it switches the stack pointer
        # Unicorn: a0-a7 are 1-8, d0-d7 9-16. d0 d1=0 (one byte a row),
        # d3=15 rows, d4 ink; a1=0 (x), a2 the bytes, a3 the rows; sp.
        for r, v in ((9, 0), (10, 0), (12, 15), (13, INK), (2, 0), (3, BYTES), (4, TABLE), (8, STACK)):
            reg(r, v)
        ck(u.uc_emu_start(h, dispatch-6, STOP, 0, 100000))
        b = C.create_string_buffer(16*STRIDE); ck(u.uc_mem_read(h, ROWS, b, 16*STRIDE)); out = b.raw
    finally:
        u.uc_close(h)
    assert all(c == PAPER for n in range(16) for c in out[n*STRIDE+4:(n+1)*STRIDE]), 'drew outside the 4 pixels'
    assert all(c in (PAPER, INK) for c in out), 'not the ink colour'
    return [tuple(out[n*STRIDE+x] == INK for x in range(4)) for n in range(16)]


def expected(n):
    return tuple(bool(n >> (3-x) & 1) for x in range(4))


def check(original, fixed, dispatch):
    """The original loses only $0D's pixel 3 (drawing $0C); the fixed one draws every nibble."""
    before, after = rows(original, dispatch), rows(fixed, dispatch)
    assert [n for n in range(16) if before[n] != expected(n)] == [13] and before[13] == expected(12), before
    assert all(after[n] == expected(n) for n in range(16)), after
    return dict(original_wrong=[13], fixed_wrong=[])
