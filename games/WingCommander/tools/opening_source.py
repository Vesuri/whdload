"""Shared opening adapters; only generated tmp/ files contain native bytes."""
import hashlib
from variants import get
from german_map import Symbols

# All entries are code-hunk 3 offsets and full instruction spans. The OCS map
# is independently checked against its pinned executable; common layout is not
# permission to reuse native addresses or A4 data offsets.
# Burst rebase is in setup, before the loop. Do not overwrite its interior
# branch target at $146c (OCS $13b2) with an entry trampoline.
STAGES=((0xd12,8,'begin'),(0xee0,6,'animation'),(0xfb4,10,'expression'),
        (0x10cc,10,'separation'),(0x11a8,8,'flight'),(0x12c0,8,'particles'),
        (0x145c,6,'burst'),(0xde0,6,'end'))
TICKS=(0xf1a,0xf88,0x1010,0x13de,0x14d8)
SEP_DRAW=0x115e     # separation piece draw call (hunk 3, relocated jsr)


def renderer(variant):
    """Scaled bitmap renderer (hunk 0), its x/y 8.8 load span and x argument."""
    return (0x2f3a0,0x2f3d6,64) if variant=='ocs' else (0x2ec98,0x2ecd2,68)


def code_patches(variant):
    """Hunk-0 patches: the renderer's two 8.8 loads (16 bytes)."""
    entry,load,_=renderer(variant)
    return [(load,16,'opening_sep_fixed',0x4eb9)]


def specification(variant):
    shift=0xba if variant=='ocs' else 0
    stages=[(o-shift,w,n) for o,w,n in STAGES]
    patches=[(o,w,'opening_stage_'+n,0x4ef9) for o,w,n in stages]
    # Orchestra (forward and backward loops), expression, fireworks twice.
    kinds={0xf1a:'orchestra',0xf88:'orchestra',0x1010:'tick',0x13de:'fireworks',0x14d8:'fireworks'}
    patches += [(o-shift,6,f'opening_{kinds[o]}_input',0x4eb9) for o in TICKS]
    patches += [(0x1194-shift,10,'opening_separation_sample',0x4eb9),
                (0x11ca-shift,6,'opening_flight_prepare',0x4eb9),
                (0x129a-shift,6,'opening_flight_sample',0x4eb9)]
    # Separation piece loop: s*vx, s*vy (position) and s*vy<<2 (scale).
    patches += [(0x10f8-shift,6,'opening_sep_x',0x4eb9),(0x1102-shift,6,'opening_sep_y',0x4eb9),
                (0x1130-shift,8,'opening_sep_scale',0x4eb9),
                (SEP_DRAW-shift,6,'opening_sep_draw',0x4eb9)]
    return stages,patches,[(0x1200-shift,14)]


def source(root,variant):
    v=get(variant);game=(root/v.GAME).read_bytes()
    if hashlib.sha256(game).hexdigest()!=v.GAME_SHA:raise ValueError('changed opening input')
    code=game[v.HUNKS[3][0]:v.HUNKS[3][0]+v.HUNKS[3][1]]
    code0=game[v.HUNKS[0][0]:v.HUNKS[0][0]+v.HUNKS[0][1]]
    entry,load,xarg=renderer(variant)
    expected=bytes.fromhex(f'342f{xarg:04x}48c2e182362f{xarg+2:04x}48c3e183')
    if code0[load:load+16]!=expected:raise ValueError('renderer load span changed')
    if code[SEP_DRAW-(0xba if variant=='ocs' else 0):][:6]!=bytes.fromhex('4eb9')+entry.to_bytes(4,'big'):
        raise ValueError('separation draw call changed')
    stages,patches,nops=specification(variant)
    S=Symbols(variant)
    input_offset=0x180c4 if variant=='ocs' else 0x1898a
    lines=[f'OPEN_FIELD equ {S.a4(v.A4["field_clock"])}',
           f'OPEN_COUNTDOWN equ {S.a4(-32592 if variant=="ocs" else -32624)}',
           f'SEP_XARG equ {xarg}',
           (root/'src/opening_clock.s').read_text()]
    resumes=[]
    for off,width,name in stages:
        raw=code[off:off+width]
        # Entry spans contain no relocated operands/PC-relative instructions.
        lines += ['opening_stage_'+name+':',
                  ' bsr.w '+('opening_begin' if name=='begin' else 'opening_end' if name=='end' else 'opening_rebase'),
                  S.copy(code,off,off+width,3),
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
        calls={x-(0xba if variant=='ocs' else 0):input_offset for x in TICKS}
        calls[SEP_DRAW-(0xba if variant=='ocs' else 0)]=entry
        if off in calls:
            if raw[:2]!=bytes.fromhex('4eb9') or int.from_bytes(raw[2:6],'big')!=calls[off]:raise ValueError('opening call site changed')
            lines += [f' cmpi.w #$4eb9,{S.code(off,3)}(a2)',' bne.w opening_bad',
                      ' move.l a0,d0',f' addi.l #{S.code(calls[off])},d0',f' cmp.l {S.code(off+2,3)}(a2),d0',' bne.w opening_bad']
        else:
            for i in range(0,width,2):
                lines += [f' cmpi.w #{S.word(code,off+i,3)},{S.code(off+i,3)}(a2)',' bne.w opening_bad']
    for off,width in nops:
        for i in range(0,width,2):
            lines += [f' cmpi.w #{S.word(code,off+i,3)},{S.code(off+i,3)}(a2)',' bne.w opening_bad']
    for off,width,_,_ in code_patches(variant):
        # Beyond a 68000 16-bit displacement: address the span through A1.
        lines += [' movea.l a0,a1',f' adda.l #{S.code(off)},a1']
        for i in range(0,width,2):
            lines += [f' cmpi.w #{S.word(code0,off+i)},(a1)+',' bne.w opening_bad']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts']
    lines+=head('opening_install')
    for name,off in resumes:
        lines += [f' lea {S.code(off,3)}(a2),a1',f' lea {name}+2(pc),a3',' move.l a1,(a3)']
    lines += [' movea.l a0,a1',f' adda.l #{S.code(input_offset)},a1',' lea opening_input_native+2(pc),a3',' move.l a1,(a3)']
    lines += [' movea.l a0,a1',f' adda.l #{S.code(entry)},a1',' lea opening_sep_renderer+2(pc),a3',' move.l a1,(a3)']
    for off,width,label,op in code_patches(variant):
        lines += [' movea.l a0,a1',f' adda.l #{S.code(off)},a1',f' move.w #${op:x},(a1)+',f' lea {label}(pc),a3',' move.l a3,(a1)+']
        lines += [' move.w #$4e71,(a1)+']*((width-6)//2)
    for off,width,label,op in patches:
        lines += [f' move.w #${op:x},{S.code(off,3)}(a2)',f' lea {label}(pc),a1',f' move.l a1,{S.code(off+2,3)}(a2)']
        for at in range(off+6,off+width,2):lines += [f' move.w #$4e71,{S.code(at,3)}(a2)']
    for off,width in nops:
        for at in range(off,off+width,2):lines += [f' move.w #$4e71,{S.code(at,3)}(a2)']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','opening_bad:',
            ' movem.l (sp)+,d0-d7/a0-a6',
            ' bra.w '+('wrong_revision' if variant=='ocs' else 'timing_bad')]
    return '\n'.join(lines)+'\n'
