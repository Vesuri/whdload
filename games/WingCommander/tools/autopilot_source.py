"""Pinned, separately mapped waypoint fly-by call sites."""
import hashlib
from variants import get


def site(variant):
    return 0x12d0 if variant == 'ocs' else 0x1396


def source(root, variant):
    v = get(variant)
    raw = (root / v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest() != v.GAME_SHA:
        raise ValueError('changed autopilot input')
    code = raw[44:44 + v.HUNKS[0][1]]
    off = site(variant)
    ocs = variant == 'ocs'
    assert code[off:off + 6] == bytes.fromhex('4ebafacc5c4f')
    lines = [(root / 'whdload/autopilot_clock.s').read_text()]
    fix = [('autopilot_camera', 0x6e24 if ocs else 0x70ae),
           ('autopilot_resume', off + 6)]
    overlays = (0x2018, 0x404, 0x371e) if ocs else (0x22a0, 0x402, 0x39a4)
    lines += ['autopilot_overlay:']
    for i, target in enumerate(overlays):
        label = f'autopilot_overlay{i}'
        lines += [label + ': jsr $0']
        fix.append((label, target))
    lines += [' rts']
    for label, _ in fix[:2]:
        lines += [label + ': jmp $0']
    lines += ['autopilot_guard:']
    for i in range(0, 6, 2):
        lines += [f' cmpi.w #${int.from_bytes(code[off+i:off+i+2], "big"):x},${off+i:x}(a0)',
                  ' bne.w modal_bad_target']
    lines += [' rts', 'autopilot_install:', ' movem.l d0/a1,-(sp)']
    for label, target in fix:
        lines += [' move.l a0,d0', f' addi.l #${target:x},d0',
                  f' lea {label}+2(pc),a1', ' move.l d0,(a1)']
    lines += [f' move.w #$4ef9,${off:x}(a0)', ' lea autopilot_entry(pc),a1',
              f' move.l a1,${off+2:x}(a0)', ' movem.l (sp)+,d0/a1', ' rts']
    return '\n'.join(lines) + '\n'
