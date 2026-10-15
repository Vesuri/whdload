"""Separately mapped OCS/CD32 launch hooks. Native spans stay in tmp/."""
import hashlib
from variants import get


def specification(variant):
    ocs=variant=='ocs'
    tunnel=(0x1a4e2,6,0x1a544) if ocs else (0x1b22a,6,0x1b28c)
    exterior=(0x1d9e4,0x1da38,0x1dada) if ocs else (0x1e71c,0x1e770,0x1e812)
    return [tunnel]+[(off,6,None) for off in exterior]


def source(root, variant):
    v=get(variant);raw=(root/v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=v.GAME_SHA:raise ValueError('changed launch input')
    code=raw[v.HUNKS[0][0]:v.HUNKS[0][0]+v.HUNKS[0][1]]
    ocs=variant=='ocs'
    lines=[f'EXT_POSITION equ {0x407e if ocs else 0x488e}',f'EXT_SCROLL equ {0x3f5a if ocs else 0x476a}',f'LAUNCH_COLOUR equ {0x8e2 if ocs else 0x1154}',
           f'LAUNCH_SURFACE equ {0x8e4 if ocs else 0x1156}',
           f'LAUNCH_IMAGE equ {-0x5d26 if ocs else -0x5d10}',
           (root/'whdload/launch_clock.s').read_text()]
    fix=[('launch_resume',specification(variant)[0][2]),('launch_zoom',0x2f3a0 if ocs else 0x2ec98),
         ('launch_hud',0x4460 if ocs else 0x46e6),('launch_exterior_pose',0x1d5a8 if ocs else 0x1e2d8),('launch_exterior_native',0x1d680 if ocs else 0x1e3b2)]
    for label,_ in fix:lines.append(label+': jmp $0')
    for i in range(3):
        lines += [f'launch_entry{i+1}:',' move.l d0,-(sp)',f' moveq #{i},d0',' bsr.w launch_exterior_wait',' move.l (sp)+,d0',' bra.w modal_input']
    lines+=['launch_entry0: bra.w launch_loop','launch_guard:',' movem.l d0-d7/a0-a6,-(sp)']
    for off,width,_ in specification(variant):
        assert code[off:off+2]==bytes.fromhex('4eb9')
        lines += [f' cmpi.w #$4eb9,${off:x}(a0)',' bne.w launch_bad',' move.l a0,d0',
                  f' addi.l #${int.from_bytes(code[off+2:off+6],"big"):x},d0',f' cmp.l ${off+2:x}(a0),d0',' bne.w launch_bad']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','launch_install:',' movem.l d0-d7/a0-a6,-(sp)']
    for label,target in fix:
        lines+=[' move.l a0,d0',f' addi.l #${target:x},d0',f' lea {label}+2(pc),a1',' move.l d0,(a1)']
    for i,(off,width,_) in enumerate(specification(variant)):
        lines += [f' move.w #${0x4ef9 if i==0 else 0x4eb9:x},${off:x}(a0)',f' lea launch_entry{i}(pc),a1',f' move.l a1,${off+2:x}(a0)']
    lines += [' movem.l (sp)+,d0-d7/a0-a6',' rts','launch_bad:',
              ' movem.l (sp)+,d0-d7/a0-a6',' bra.w modal_bad_target']
    text='\n'.join(lines)+'\n'
    text=text.replace('bsr.w timing_rate','lea launch_exterior_wait(pc),a0\n        adda.l #timing_rate-launch_exterior_wait,a0\n        jsr (a0)')
    if ocs:
        from shared_cpu import select
        text=select(text,'68000')
    return text
