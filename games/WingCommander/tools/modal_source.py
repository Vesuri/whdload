"""Pinned, variant-specific modal scene adapters. Native spans stay in tmp/."""
import hashlib
from variants import get
from german_map import Symbols


def specification(variant):
    ocs=variant=="ocs"
    upper,feet=(0x1d0c6,0x1d1f6) if ocs else (0x1ddf4,0x1df24)
    sim=0x19bda if ocs else 0x1a8b2
    begin=(0x24eea,0x260f2) if ocs else (0x25d18,0x26fe8)
    wait=(0x24f16,0x2611e) if ocs else (0x25d44,0x27014)
    patches=[(upper,6,'modal_run_upper'),(feet,6,'modal_run_feet'),(sim,8,'modal_dispatch'),(0x24ae0 if ocs else 0x25922,8,'modal_portraits')]
    patches += list(zip((0x26566,0x2664a,0x26670) if ocs else (0x27448,0x2752c,0x27552), (6,6,6), ('modal_label_begin','modal_label_print','modal_label_end')))
    patches += [(off,6,'modal_room_input') for off in ((0x24f2c,0x26138) if ocs else (0x25d5a,0x2702e))]
    patches += [(off,6,'modal_room_'+kind+str(i)) for kind,sites in [('begin',begin),('wait',wait)] for i,off in enumerate(sites)]
    patches += [(0x19a94 if ocs else 0x1a7a8,8,'modal_death_begin'),
                (0x19b02 if ocs else 0x1a7fe,6,'modal_death_publish')]
    for i,publish in enumerate((0x230da,0x23340,0x1c474) if ocs else (0x23f3c,0x241a2,0x1d19e)):
        patches += [(publish,6,f'modal_crowd_publish{i}')]
    return upper,feet,sim,begin,wait,patches


def source(root, variant):
    v=get(variant); raw=(root/v.GAME).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=v.GAME_SHA:raise ValueError('changed modal input')
    code=raw[44:44+v.HUNKS[0][1]]
    ocs=variant=='ocs'
    upper,feet,sim,begin,wait,patches=specification(variant)
    S=Symbols(variant)
    fields=dict(MODAL_TEXT_CONTEXT=-0xc74 if ocs else -0x8de,MODAL_LABEL_CONTEXT=0x1a0 if ocs else 0xa8c,MODAL_TRANSPARENT=0x21fa if ocs else 0x2c6c,MODAL_LABEL_SURFACE=0x1b8 if ocs else 0xaa4,MODAL_LABEL_COLOUR=0x1b7 if ocs else 0xaa3,MODAL_FIELD=v.A4['field_clock'],MODAL_COUNTDOWN=-32592 if ocs else -32624,
                MODAL_CENTRE_X=-4184 if ocs else -4314,MODAL_CENTRE_Y=-4182 if ocs else -4312,
                MODAL_ABORT=-0x707c if ocs else -0x7094,MODAL_CONTEXT=-31670 if ocs else -31696,
                BAR_POINTERS=0x84 if ocs else 0x970,BAR_RNG=-4196 if ocs else -4326,
                BAR_DRAW_COUNT=2272 if ocs else 4434)
    fields.update(dict(zip(('BAR_SURFACE','BAR_COLOUR','BAR_STATIC','BAR_STATIC_COUNT','BAR_MOVING','BAR_MOVING_COUNT','BAR_IMAGE'),
                           (-754,2274,0x40e2,0x40de,0x411e,0x40e0,-0x2d70) if ocs else
                           (0x5fa,0x1154,0x48f2,0x48ee,0x492e,0x48f0,-0x2df2))))
    lines=[*(f'{k} equ {S.a4(n)}' for k,n in fields.items()),
           'MODAL_CLOCK equ '+('ocs_clock_state' if ocs else 'timing_clock'),
           'MODAL_HZ equ '+('ocs_clock_hz' if ocs else 'timing_hz'),
           (root/'src/modal_clock.s').read_text()]
    room_tables=[S.a4(n) for n in ((-0x4b78,-0x4ab8) if ocs else (-0x4b8a,-0x4aca))]
    fix=[]
    def native(label, target):
        lines.append(label+': jmp $0');fix.append((label,target))
    for label,target in [('modal_label_native_reset',0x30556 if ocs else 0x2fcd0),
                          ('modal_label_native_clear',0x322e0 if ocs else 0x31cd6),
                          ('modal_label_native_print',0x2cc80 if ocs else 0x2f76a),
                          ('modal_label_native_cursor',0x31cea if ocs else 0x316e6),
                          ('modal_bar_clear',0x322e0 if ocs else 0x31cd6),
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
        lines+=['modal_'+name+'_resume:',S.copy(code,off,off+6)]
        native('modal_'+name+'_tail',off+6)
    for off,width,label in patches:
        if label.startswith('modal_crowd_publish'):
            lines += [label+':', ' tst.w '+('d2' if label.endswith('0') else 'd4'), ' bne.s .ready', ' bsr.w modal_crowd_rebase', '.ready:', ' bsr.w '+label+'_native', ' bra.w modal_crowd_wait']
            native(label+'_native',int.from_bytes(code[off+2:off+6],'big'))
    death=0x19a94 if ocs else 0x1a7a8
    lines += ['modal_death_begin:', ' bsr.w modal_death_rebase',
              S.copy(code,death,death+8)]
    native('modal_death_resume',death+8)
    native('modal_death_native_publish',0xb80 if ocs else 0xc40)
    portrait=0x24ae0 if ocs else 0x25922
    lines+=['modal_portrait_native:',S.copy(code,portrait,portrait+8)]
    native('modal_portrait_resume',portrait+8)
    lines+=['modal_dispatch:',' tst.w 14(sp)',' beq.w modal_simulator',
            S.copy(code,sim,sim+8)]
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
    lines+=['modal_guard:',' bsr.w funeral_guard',' bsr.w landing_guard',' bsr.w ejection_guard',' bsr.w autopilot_guard',' bsr.w launch_guard',' movem.l d0-d7/a0-a6,-(sp)']
    for off,width,_ in patches:
        if code[off:off+2]==bytes.fromhex('4eb9'):
            target=int.from_bytes(code[off+2:off+6],'big')
            lines += [f' cmpi.w #$4eb9,{S.code(off)}(a0)',' bne.w modal_bad',
                      ' move.l a0,d0',f' addi.l #{S.code(target)},d0',f' cmp.l {S.code(off+2)}(a0),d0',' bne.w modal_bad']
        else:
            for n in range(0,width,2):lines += [f' cmpi.w #{S.word(code,off+n)},{S.code(off+n)}(a0)',' bne.w modal_bad']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','modal_install:',' bsr.w funeral_install',' bsr.w landing_install',' bsr.w ejection_install',' bsr.w autopilot_install',' bsr.w launch_install',' movem.l d0-d7/a0-a6,-(sp)']
    for label,target in fix:
        lines += [' move.l a0,d0',f' addi.l #{S.code(target)},d0',f' lea {label}+2(pc),a1',' move.l d0,(a1)']
    for off,width,label in patches:
        op=0x4eb9 if off in begin+wait or label in ('modal_room_input','modal_death_publish') or label.startswith(('modal_label_','modal_crowd_publish')) else 0x4ef9
        lines += [f' move.w #${op:x},{S.code(off)}(a0)',f' lea {label}(pc),a1',f' move.l a1,{S.code(off+2)}(a0)']
        for n in range(6,width,2):lines += [f' move.w #$4e71,{S.code(off+n)}(a0)']
    lines+=[' movem.l (sp)+,d0-d7/a0-a6',' rts','modal_bad:',
            ' movem.l (sp)+,d0-d7/a0-a6','modal_bad_target:',' bra.w '+('wrong_revision' if ocs else 'timing_bad')]
    from launch_source import source as launch_source
    lines.append(launch_source(root,variant))
    from autopilot_source import source as autopilot_source
    lines.append(autopilot_source(root,variant))
    from ejection_source import source as ejection_source
    lines.append(ejection_source(root,variant))
    from landing_source import source as landing_source
    lines.append(landing_source(root,variant))
    from funeral_source import source as funeral_source
    lines.append(funeral_source(root,variant))
    text='\n'.join(lines)+'\n'
    if ocs:
        from shared_cpu import select
        text=select(text,'68000')
        text=text.replace(' bra.w wrong_revision',' lea modal_bad(pc),a0\n adda.l #wrong_revision-modal_bad,a0\n jmp (a0)')
    else:
        text=text.replace('bsr.w timing_rate','bsr.l timing_rate').replace(' bra.w timing_bad',' bra.l timing_bad')
    return text
