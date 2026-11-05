"""Separately mapped landing clocks and read-only redraw fragments."""
import hashlib
from capstone import Cs, CS_ARCH_M68K, CS_MODE_BIG_ENDIAN, CS_MODE_M68K_000
from variants import get


def specification(variant):
    return ([(0x1a632,6,'landing_entry0'),(0x1a962,16,'landing_entry1'),
             (0x1a774,6,'landing_wait'),(0x1ab36,6,'landing_wait'),
             (0x1a64c,10,'landing_skip_clear'),(0x1a6a6,6,'landing_skip_draw')] if variant=='ocs' else
            [(0x1b37a,6,'landing_entry0'),(0x1b6aa,16,'landing_entry1'),
             (0x1b4bc,6,'landing_wait'),(0x1b87e,6,'landing_wait'),
             (0x1b394,10,'landing_skip_clear'),(0x1b3ee,6,'landing_skip_draw')])


def source(root,variant):
    v=get(variant);raw=(root/v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=v.GAME_SHA:raise ValueError('changed landing input')
    code=raw[44:44+v.HUNKS[0][1]];ocs=variant=='ocs'
    lines=[f'LANDING_SCROLL equ {0x3f5a if ocs else 0x476a}',(root/'src/landing_clock.s').read_text()]
    fix=[]
    for name,target in [('landing_skip_clear',0x1a65c if ocs else 0x1b3a4),('landing_skip_draw',0x1a750 if ocs else 0x1b498)]:
        lines.append(name+': jmp $0');fix.append((name,target))
    dis=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_000)
    def fragment(name,start,end,substitutions=None):
        substitutions=substitutions or {}
        lines.append(name+':')
        for ins in dis.disasm(code[start:end],start):
            lines.append(f'{name}_{ins.address:x}:')
            op=bytes(ins.bytes)
            if ins.address in substitutions:
                lines.extend(substitutions[ins.address]);continue
            if op[:2]==b'\x4e\xb9':
                label=f'{name}_call{ins.address:x}'
                lines.append(label+': jsr $0');fix.append((label,int.from_bytes(op[2:],'big')))
            elif op[0]>>4==6:
                delta=int.from_bytes(op[2:4] if op[1]==0 else op[1:2],'big',signed=True)
                target=ins.address+2+delta
                assert start<=target<=end,(name,ins)
                lines.append(f' {ins.mnemonic.split(".")[0]}.w {name}_{target:x}')
            else:
                assert 'pc' not in ins.op_str and not ins.mnemonic.startswith(('j','db'))
                lines.append(' dc.b '+','.join(str(x) for x in op))
        lines.append(f'{name}_{end:x}:')
    for stage,(off,width,_) in enumerate(specification(variant)[:2]):
        lines += [f'landing_entry{stage}:',' move.l d0,-(sp)',f' moveq #{stage},d0',
                  ' bsr.w landing_capture',' move.l (sp)+,d0']
        fragment(f'landing_displaced{stage}',off,off+width)
        label=f'landing_resume{stage}'
        lines.append(label+': jmp $0');fix.append((label,off+width))
    fragment('landing_draw0',0x1a64c if ocs else 0x1b394,0x1a65c if ocs else 0x1b3a4)
    fragment('landing_pose0',0x1a6a6 if ocs else 0x1b3ee,0x1a750 if ocs else 0x1b498,
             {0x1a6c6 if ocs else 0x1b40e:[' bsr.w landing_scale']})
    lines.append(' rts')
    fragment('landing_draw1',0x1a962 if ocs else 0x1b6aa,0x1aa52 if ocs else 0x1b79a,
             {0x1a96e if ocs else 0x1b6b6:[' bsr.w landing_scale']})
    # Native argument cleanup follows the draw span, after CMP in the original.
    lines += [' lea 28(sp),sp',' rts','landing_rate:']
    lines += [' lea landing_rate(pc),a0',' adda.l #timing_rate-landing_rate,a0',' jmp (a0)']
    lines += ['landing_guard:',' movem.l d0,-(sp)']
    for off,width,_ in specification(variant):
        if code[off:off+2]==b'\x4e\xb9':
            target=int.from_bytes(code[off+2:off+6],'big')
            lines += [f' cmpi.w #$4eb9,${off:x}(a0)',' bne.w landing_bad',' move.l a0,d0',
                      f' addi.l #${target:x},d0',f' cmp.l ${off+2:x}(a0),d0',' bne.w landing_bad']
        else:
            for n in range(0,width,2):lines += [f' cmpi.w #${int.from_bytes(code[off+n:off+n+2],"big"):x},${off+n:x}(a0)',' bne.w landing_bad']
    lines += [' move.l (sp)+,d0',' rts','landing_bad:',' move.l (sp)+,d0',' bra.w modal_bad_target',
              'landing_install:',' movem.l d0/a1,-(sp)']
    for label,target in fix:
        lines += [' move.l a0,d0',f' addi.l #${target:x},d0',f' lea {label}+2(pc),a1',' move.l d0,(a1)']
    for off,width,label in specification(variant):
        lines += [f' move.w #${0x4eb9 if label=="landing_wait" else 0x4ef9:x},${off:x}(a0)',
                  f' lea {label}(pc),a1',f' move.l a1,${off+2:x}(a0)']
        for n in range(6,width,2):lines.append(f' move.w #$4e71,${off+n:x}(a0)')
    lines += [' movem.l (sp)+,d0/a1',' rts']
    return '\n'.join(lines)+'\n'
