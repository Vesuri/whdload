"""Pinned, variant-specific modal scene adapters. Native spans stay in tmp/."""
import hashlib
from variants import get


def specification(variant):
    ocs=variant=="ocs"
    upper,feet=(0x1d0c6,0x1d1f6) if ocs else (0x1ddf4,0x1df24)
    sim=0x19bda if ocs else 0x1a8b2
    begin=(0x24eea,0x260f2) if ocs else (0x25d18,0x26fe8)
    wait=(0x24f16,0x2611e) if ocs else (0x25d44,0x27014)
    patches=[(upper,6,'modal_run_upper'),(feet,6,'modal_run_feet'),(sim,8,'modal_dispatch'),(0x24ae0 if ocs else 0x25922,8,'modal_portraits')]
    patches += [(off,6,'modal_room_input') for off in ((0x24f2c,0x26138) if ocs else (0x25d5a,0x2702e))]
    patches += [(off,6,'modal_room_'+kind+str(i)) for kind,sites in [('begin',begin),('wait',wait)] for i,off in enumerate(sites)]
    return upper,feet,sim,begin,wait,patches


def source(root, variant):
    v=get(variant); raw=(root/v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=v.GAME_SHA:raise ValueError('changed modal input')
    code=raw[44:44+v.HUNKS[0][1]]
    ocs=variant=='ocs'
    upper,feet,sim,begin,wait,patches=specification(variant)
    fields=dict(MODAL_FIELD=v.A4['field_clock'],MODAL_COUNTDOWN=-32592 if ocs else -32624,
                MODAL_CENTRE_X=-4184 if ocs else -4314,MODAL_CENTRE_Y=-4182 if ocs else -4312,
                MODAL_ABORT=-0x707c if ocs else -0x7094,MODAL_CONTEXT=-31670 if ocs else -31696,
                BAR_POINTERS=0x84 if ocs else 0x970,BAR_RNG=-4196 if ocs else -4326,
                BAR_DRAW_COUNT=2272 if ocs else 4434)
    fields.update(dict(zip(('BAR_SURFACE','BAR_COLOUR','BAR_STATIC','BAR_STATIC_COUNT','BAR_MOVING','BAR_MOVING_COUNT','BAR_IMAGE'),
                           (-754,2274,0x40e2,0x40de,0x411e,0x40e0,-0x2d70) if ocs else
                           (0x5fa,0x1154,0x48f2,0x48ee,0x492e,0x48f0,-0x2df2))))
    lines=[*(f'{k} equ {n}' for k,n in fields.items()),
           'MODAL_CLOCK equ '+('ocs_clock_state' if ocs else 'timing_clock'),
           'MODAL_HZ equ '+('ocs_clock_hz' if ocs else 'timing_hz'),
           (root/'whdload/modal_clock.s').read_text()]
    room_tables=(-0x4b78,-0x4ab8) if ocs else (-0x4b8a,-0x4aca)
    fix=[]
    def native(label, target):
        lines.append(label+': jmp $0');fix.append((label,target))
    for label,target in [('modal_bar_clear',0x322e0 if ocs else 0x31cd6),
                          ('modal_bar_restore',0x24d04 if ocs else 0x25b46),
                          ('modal_room_native_input',0x26490 if ocs else 0x27372),
                          ('modal_bar_bitmap',0x2f9a6 if ocs else 0x2efe8),
                          ('modal_bar_publish',0x3260a if ocs else 0x31fc2),
                          ('modal_divide',0x2c710 if ocs else 0x2d594),
                          ('modal_text',0x13c32 if ocs else 0x13ebc),
                          ('modal_input',0x180c4 if ocs else 0x1898a),
                          ('modal_context_begin',0x13b30 if ocs else 0x13dba),
                          ('modal_context_end',0x13bc8 if ocs else 0x13e52)]:native(label,target)
    for name,off in [('upper',upper),('feet',feet)]:
        lines+=['modal_'+name+'_resume:',' dc.b '+','.join(str(x) for x in code[off:off+6])]
        native('modal_'+name+'_tail',off+6)
    portrait=0x24ae0 if ocs else 0x25922
    lines+=['modal_portrait_native:',' dc.b '+','.join(str(x) for x in code[portrait:portrait+8])]
    native('modal_portrait_resume',portrait+8)
    lines+=['modal_dispatch:',' tst.w 14(sp)',' beq.w modal_simulator',
            ' dc.b '+','.join(str(x) for x in code[sim:sim+8])]
    native('modal_sim_native',sim+8)
    for kind,sites in [('begin',begin),('wait',wait)]:
        for i,off in enumerate(sites):
            assert code[off:off+2]==bytes.fromhex('4eb9')
            # Tail-call preserves the native C argument layout.
            lines += [f'modal_room_{kind}{i}:',f' bsr.w modal_room_{kind}']
            if kind=='begin':
                lines += [' movem.l a0,-(sp)',' lea modal_bar_enabled(pc),a0',f' move.w #{1 if i==0 else 0},(a0)',
                          ' lea modal_bar_count(pc),a0',' move.w #-1,(a0)',
                          f' lea {room_tables[i]}(a4),a0',
                          ' move.l a1,-(sp)', ' lea modal_room_table(pc),a1', ' move.l a0,(a1)', ' move.l (sp)+,a1', ' movem.l (sp)+,a0']
            if kind=='wait' and i==0:lines += [' bsr.w modal_bar_capture']
            native(f'modal_room_{kind}{i}_native' ,int.from_bytes(code[off+2:off+6],'big'))
    lines+=['modal_guard:',' bsr.w launch_guard',' movem.l d0-d7/a0-a6,-(sp)']
    for off,width,_ in patches:
        if code[off:off+2]==bytes.fromhex('4eb9'):
            target=int.from_bytes(code[off+2:off+6],'big')
            lines += [f' cmpi.w #$4eb9,${off:x}(a0)',' bne.w modal_bad',
                      ' move.l a0,d0',f' addi.l #${target:x},d0',f' cmp.l ${off+2:x}(a0),d0',' bne.w modal_bad']
        else:
            for n in range(0,width,2):lines += [f' cmpi.w #${int.from_bytes(code[off+n:off+n+2],"big"):x},${off+n:x}(a0)',' bne.w modal_bad']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','modal_install:',' bsr.w launch_install',' movem.l d0-d7/a0-a6,-(sp)']
    for label,target in fix:
        lines += [' move.l a0,d0',f' addi.l #${target:x},d0',f' lea {label}+2(pc),a1',' move.l d0,(a1)']
    for off,width,label in patches:
        op=0x4eb9 if off in begin+wait or label=='modal_room_input' else 0x4ef9
        lines += [f' move.w #${op:x},${off:x}(a0)',f' lea {label}(pc),a1',f' move.l a1,${off+2:x}(a0)']
        for n in range(6,width,2):lines += [f' move.w #$4e71,${off+n:x}(a0)']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','modal_bad:',
            ' movem.l (sp)+,d0-d7/a0-a6','modal_bad_target:',' bra.w '+('wrong_revision' if ocs else 'timing_bad')]
    from launch_source import source as launch_source
    lines.append(launch_source(root,variant))
    text='\n'.join(lines)+'\n'
    if ocs:
        from shared_cpu import select
        text=select(text,'68000')
        text=text.replace(' bra.w wrong_revision',' lea modal_bad(pc),a0\n adda.l #wrong_revision-modal_bad,a0\n jmp (a0)')
    else:
        text=text.replace('bsr.w timing_rate','bsr.l timing_rate').replace(' bra.w timing_bad',' bra.l timing_bad')
    return text
