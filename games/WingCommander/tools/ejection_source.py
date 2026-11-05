"""Pinned ejection stage hooks and relocated native overlays; bytes stay in tmp/."""
import hashlib
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from variants import get


def specification(variant):
    return ([(0x19f6c, 0x1a040), (0x1a12a, 0x1a17a), (0x1a21c, 0x1a280)]
            if variant == 'ocs' else
            [(0x1ac30, 0x1ad0a), (0x1ae32, 0x1ae9c), (0x1af44, 0x1afc8)])


def source(root, variant):
    v = get(variant)
    raw = (root / v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest() != v.GAME_SHA:
        raise ValueError('changed ejection input')
    code = raw[44:44 + v.HUNKS[0][1]]
    ocs = variant == 'ocs'
    finish = 0xb80 if ocs else 0xc40
    spans = ([(0x19f78, 0x1a014), (0x1a134, 0x1a16a), (0, 0),
              (0x1a014, 0x1a030), (0x1a21c, 0x1a22a), (0x1a246, 0x1a26a)] if ocs else
             [(0x1ac3c, 0x1acd8), (0x1ae3c, 0x1ae86), (0x1af5e, 0x1af7c),
              (0x1acd8, 0x1acf4), (0x1af44, 0x1af52), (0x1af8c, 0x1afb0)])
    lines = [f'EJECTION_SLOT equ {-0x478a if ocs else -0x4764}',
             f'EJECTION_VIEW equ {-18318 if ocs else -18280}',
             f'EJECTION_SUBJECT equ {-18334 if ocs else -18296}',
             (root / 'whdload/ejection_clock.s').read_text()]
    fix = []
    dis = Cs(CS_ARCH_M68K, CS_MODE_BIG_ENDIAN | CS_MODE_M68K_000)
    # Lift only bounded native fragments. Local branches get fresh labels;
    # absolute calls are relocated by the installer. No copied PC-relative data.
    for name, (start, end) in zip(('draw0','draw1','draw2','step0','effect','explode'), spans):
        prefix = 'ejection_' + name
        lines.append(prefix + ':')
        cursor = start
        for ins in dis.disasm(code[start:end], start):
            assert ins.address == cursor
            cursor += ins.size
            lines.append(f'{prefix}_{ins.address:x}:')
            op = bytes(ins.bytes)
            if op[:2] == b'\x4e\xb9':
                target = int.from_bytes(op[2:], 'big')
                if target != finish:
                    label = f'{prefix}_call{ins.address:x}'
                    lines.append(label + ': jsr $0')
                    fix.append((label, target))
            elif op[0] == 0x67:  # the native overlay/step's local BEQ
                delta = int.from_bytes(op[2:4] if op[1] == 0 else op[1:2], 'big', signed=True)
                target = ins.address + 2 + delta
                assert start <= target <= end
                lines.append(f' beq.w {prefix}_{target:x}')
            elif op[0] == 0x6f:  # step0's BLE
                target = ins.address + 2 + int.from_bytes(op[1:2], 'big', signed=True)
                assert start <= target <= end
                lines.append(f' ble.w {prefix}_{target:x}')
            else:
                assert not ins.mnemonic.startswith(('b', 'j', 'db')) and 'pc' not in ins.op_str, ins
                lines.append(' dc.b ' + ','.join(str(x) for x in op))
        assert cursor == end
        lines.append(f'{prefix}_{end:x}:')
        if name == 'effect':
            lines.append(' addq.l #4,sp')
        lines.append(' rts')
    for i, (_, resume) in enumerate(specification(variant)):
        lines += [f'ejection_entry{i}:', ' movem.l d7/a2-a3,-(sp)', f' moveq #{i},d7',
                  ' bsr.w ejection_loop', ' movem.l (sp)+,d7/a2-a3', f'ejection_resume{i}: jmp $0']
        fix.append((f'ejection_resume{i}', resume))
    lines += ['ejection_guard:', ' movem.l d0-d1,-(sp)']
    for off, _ in specification(variant):
        if code[off:off+2] == b'\x4e\xb9':
            target = int.from_bytes(code[off+2:off+6], 'big')
            lines += [f' cmpi.w #$4eb9,${off:x}(a0)', ' bne.w ejection_bad',
                      ' move.l a0,d0', f' addi.l #${target:x},d0',
                      f' cmp.l ${off+2:x}(a0),d0', ' bne.w ejection_bad']
        else:
            for n in range(0, 6, 2):
                lines += [f' cmpi.w #${int.from_bytes(code[off+n:off+n+2],"big"):x},${off+n:x}(a0)',
                          ' bne.w ejection_bad']
    lines += [' movem.l (sp)+,d0-d1', ' rts', 'ejection_bad:',
              ' movem.l (sp)+,d0-d1', ' bra.w modal_bad_target',
              'ejection_install:', ' movem.l d0/a1,-(sp)']
    for label, target in fix:
        lines += [' move.l a0,d0', f' addi.l #${target:x},d0',
                  f' lea {label}+2(pc),a1', ' move.l d0,(a1)']
    for i, (off, _) in enumerate(specification(variant)):
        lines += [f' move.w #$4ef9,${off:x}(a0)', f' lea ejection_entry{i}(pc),a1',
                  f' move.l a1,${off+2:x}(a0)']
    lines += [' movem.l (sp)+,d0/a1', ' rts']
    return '\n'.join(lines) + '\n'
