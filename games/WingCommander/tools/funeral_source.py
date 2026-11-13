"""Guarded funeral renderer adapter; native prefix bytes remain in tmp/."""
import hashlib
from variants import get
from german_map import Symbols


def source(root, variant):
    v = get(variant)
    raw = (root / v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest() != v.GAME_SHA:
        raise ValueError('changed funeral input')
    ocs = variant == 'ocs'
    S = Symbols(variant)
    off = 0x1df12 if ocs else 0x1ec4c
    state = 0x40aa if ocs else 0x48ba
    # Funeral parameters, static stars and 64 eight-byte moving records.
    size = 0x74 + 64 * 8
    prefix = raw[44 + off:44 + off + 8]
    assert prefix == bytes.fromhex('48e73e20342c') + state.to_bytes(2, 'big')
    lines = [f'FUNERAL_STATE equ {S.a4(state) if not ocs else "$%x" % state}', f'FUNERAL_BYTES equ {size}',
             (root / 'src/funeral_clock.s').read_text(),
             'funeral_rate:', ' lea funeral_rate(pc),a0',
             ' adda.l #timing_rate-funeral_rate,a0', ' jmp (a0)',
             'funeral_native:', S.copy(raw[44:], off, off+8),
             'funeral_resume: jmp $0',
             'funeral_guard:', ' movem.l d0,-(sp)']
    for i in range(0, 8, 2):
        lines += [f' cmpi.w #{S.word(raw[44:], off+i)},{S.code(off+i)}(a0)',
                  ' bne.w funeral_bad']
    lines += [' movem.l (sp)+,d0', ' rts', 'funeral_bad:',
              ' movem.l (sp)+,d0', ' bra.w modal_bad_target',
              'funeral_install:', ' movem.l d0/a1,-(sp)',
              ' move.l a0,d0', f' addi.l #{S.code(off+8)},d0',
              ' lea funeral_resume+2(pc),a1', ' move.l d0,(a1)',
              f' move.w #$4ef9,{S.code(off)}(a0)', ' lea funeral_draw(pc),a1',
              f' move.l a1,{S.code(off+2)}(a0)', f' move.w #$4e71,{S.code(off+6)}(a0)',
              ' movem.l (sp)+,d0/a1', ' rts']
    return '\n'.join(lines) + '\n'
