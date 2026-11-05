"""Shared opening adapters; only generated tmp/ files contain native bytes."""
import hashlib
from variants import get

# All entries are code-hunk 3 offsets and full instruction spans. The OCS map
# is independently checked against its pinned executable; common layout is not
# permission to reuse native addresses or A4 data offsets.
# Burst rebase is in setup, before the loop. Do not overwrite its interior
# branch target at $146c (OCS $13b2) with an entry trampoline.
STAGES=((0xd12,8,'begin'),(0xee0,6,'animation'),(0xfb4,10,'expression'),
        (0x10cc,10,'separation'),(0x11a8,8,'flight'),(0x12c0,8,'particles'),
        (0x145c,6,'burst'),(0xde0,6,'end'))
TICKS=(0xf1a,0xf88,0x1010,0x13de,0x14d8)


def specification(variant):
    shift=0xba if variant=='ocs' else 0
    stages=[(o-shift,w,n) for o,w,n in STAGES]
    patches=[(o,w,'opening_stage_'+n,0x4ef9) for o,w,n in stages]
    patches += [(o-shift,6,'opening_fireworks_input' if o in (0x13de,0x14d8) else 'opening_tick_input',0x4eb9) for o in TICKS]
    patches += [(0x1194-shift,10,'opening_separation_sample',0x4eb9),
                (0x11ca-shift,6,'opening_flight_prepare',0x4eb9),
                (0x129a-shift,6,'opening_flight_sample',0x4eb9)]
    return stages,patches,[(0x1200-shift,14)]


def source(root,variant):
    v=get(variant);game=(root/v.GAME).read_bytes()
    if hashlib.sha256(game).hexdigest()!=v.GAME_SHA:raise ValueError('changed opening input')
    code=game[v.HUNKS[3][0]:v.HUNKS[3][0]+v.HUNKS[3][1]]
    stages,patches,nops=specification(variant)
    input_offset=0x180c4 if variant=='ocs' else 0x1898a
    lines=[f'OPEN_FIELD equ {v.A4["field_clock"]}',
           f'OPEN_COUNTDOWN equ {-32592 if variant=="ocs" else -32624}',
           (root/'src/opening_clock.s').read_text()]
    resumes=[]
    for off,width,name in stages:
        raw=code[off:off+width]
        # Entry spans contain no relocated operands/PC-relative instructions.
        lines += ['opening_stage_'+name+':',
                  ' bsr.w '+('opening_begin' if name=='begin' else 'opening_end' if name=='end' else 'opening_rebase'),
                  ' dc.b '+','.join(str(x) for x in raw),
                  'opening_resume_'+name+': jmp $0']
        resumes.append(('opening_resume_'+name,off+width))
    # Both installer helpers preserve the caller's original register ABI.
    # A0 is the first game hunk. Follow its real segment chain to hunk 3.
    def head(label):
        return [label+':',' movem.l d0-d7/a0-a6,-(sp)',' movea.l a0,a2',
                *([' move.l -4(a2),d0',' lsl.l #2,d0',' addq.l #4,d0',' movea.l d0,a2']*3)]
    lines+=head('opening_guard')
    for off,width,_,_ in patches:
        raw=code[off:off+width]
        if off in [x-(0xba if variant=='ocs' else 0) for x in TICKS]:
            if raw[:2]!=bytes.fromhex('4eb9') or int.from_bytes(raw[2:6],'big')!=input_offset:raise ValueError('opening input site changed')
            lines += [f' cmpi.w #$4eb9,${off:x}(a2)',' bne.w opening_bad',
                      ' move.l a0,d0',f' addi.l #${input_offset:x},d0',f' cmp.l ${off+2:x}(a2),d0',' bne.w opening_bad']
        else:
            for i in range(0,width,2):
                lines += [f' cmpi.w #${int.from_bytes(raw[i:i+2],"big"):x},${off+i:x}(a2)',' bne.w opening_bad']
    for off,width in nops:
        for i in range(0,width,2):
            lines += [f' cmpi.w #${int.from_bytes(code[off+i:off+i+2],"big"):x},${off+i:x}(a2)',' bne.w opening_bad']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts']
    lines+=head('opening_install')
    for name,off in resumes:
        lines += [f' lea ${off:x}(a2),a1',f' lea {name}+2(pc),a3',' move.l a1,(a3)']
    lines += [' movea.l a0,a1',f' adda.l #${input_offset:x},a1',' lea opening_input_native+2(pc),a3',' move.l a1,(a3)']
    for off,width,label,op in patches:
        lines += [f' move.w #${op:x},${off:x}(a2)',f' lea {label}(pc),a1',f' move.l a1,${off+2:x}(a2)']
        for at in range(off+6,off+width,2):lines += [f' move.w #$4e71,${at:x}(a2)']
    for off,width in nops:
        for at in range(off,off+width,2):lines += [f' move.w #$4e71,${at:x}(a2)']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','opening_bad:',
            ' movem.l (sp)+,d0-d7/a0-a6',
            ' bra.w '+('wrong_revision' if variant=='ocs' else 'timing_bad')]
    return '\n'.join(lines)+'\n'
