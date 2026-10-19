"""Guarded funeral renderer adapter; native prefix bytes remain in tmp/."""
import hashlib
from variants import get


def source(root, variant):
    v = get(variant)
    raw = (root / v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest() != v.GAME_SHA:
        raise ValueError('changed funeral input')
    ocs = variant == 'ocs'
    off = 0x1df12 if ocs else 0x1ec4c
    state = 0x40aa if ocs else 0x48ba
    # Funeral parameters, static stars and 64 eight-byte moving records.
    size = 0x74 + 64 * 8
    prefix = raw[44 + off:44 + off + 8]
    assert prefix == bytes.fromhex('48e73e20342c') + state.to_bytes(2, 'big')
    lines = [f'FUNERAL_STATE equ ${state:x}', f'FUNERAL_BYTES equ {size}',
             (root / 'whdload/funeral_clock.s').read_text(),
             'funeral_rate:', ' lea funeral_rate(pc),a0',
             ' adda.l #timing_rate-funeral_rate,a0', ' jmp (a0)',
             'funeral_native:', ' dc.b ' + ','.join(map(str, prefix)),
             'funeral_resume: jmp $0',
             'funeral_guard:', ' movem.l d0,-(sp)']
    for i in range(0, 8, 2):
        lines += [f' cmpi.w #${int.from_bytes(prefix[i:i+2], "big"):x},${off+i:x}(a0)',
                  ' bne.w funeral_bad']
    lines += [' movem.l (sp)+,d0', ' rts', 'funeral_bad:',
              ' movem.l (sp)+,d0', ' bra.w modal_bad_target',
              'funeral_install:', ' movem.l d0/a1,-(sp)',
              ' move.l a0,d0', f' addi.l #${off+8:x},d0',
              ' lea funeral_resume+2(pc),a1', ' move.l d0,(a1)',
              f' move.w #$4ef9,${off:x}(a0)', ' lea funeral_draw(pc),a1',
              f' move.l a1,${off+2:x}(a0)', f' move.w #$4e71,${off+6:x}(a0)',
              ' movem.l (sp)+,d0/a1', ' rts']
    return '\n'.join(lines) + '\n'
