#!/usr/bin/env python3
"""Build the C4–E1 OCS allocation/publication/clock candidate; generated slave in tmp/."""
import argparse
import hashlib
import json
import struct
from ocs_reconstruct import ROOT, new_output, guard_game, SLAVE_SHA, require
from ocs_c2p import assemble, source as converter_source, candidates
from ocs_backend import source as backend_source, OPTIONS
from variants import ocs

TAIL=0x14a8
NATIVE={'OCS_CHIP_ALLOC':0x33b60,'OCS_REGISTER':0x33c8e,
        'OCS_SURFACE_CREATE':0x31dc4,'OCS_SURFACE_FREE':0x32476,
        'OCS_WAIT':0x32990,'OCS_SUBMIT_BODY':0x32924,
        'OCS_COMPLETE':0x32e06,'OCS_CONVERSION':0x324a8,
        'OCS_STAMP':0x32916,'OCS_DISPLAY_CREATE':0x33200,
        'OCS_PUBLIC_ALLOC':0x33b76,'OCS_DISPLAY_FREE':0x32526,
        'OCS_SURFACE_FREE_BODY':0x3247c,'OCS_INPUT':0x345a8,
        'OCS_PRIMARY_CLOSE':0xcac,
        'OCS_DISPLAY_STATE':0x331b8,'OCS_COPPER_LOCK':0x33a6c,
        'OCS_PUBLISH_INDEX':0x3385a,'OCS_ROTATE_BODY':0x3342e,
        'OCS_CLEAR_BODY':0x33350,'OCS_PIXEL_BODY':0x333ba,
        'OCS_CLOSE_BODY':0x334bc,'OCS_VBL_CALLBACK':0x340b4,
        'OCS_VBL_RETURN':0x342c8,'OCS_VIEW_CHANGE':0x6e38,
        'OCS_SCRATCH_BODY':0x32512,'OCS_INPUT_PREPARE':0x182ce,'OCS_INPUT_BODY':0x18d1c}
HOOKS=((0x32476,'ocs_source_free',0x4ef9),
       (0x324c0,'display_create_checked',0x4ef9),
       (0x31e1e,'ocs_source_allocate',0x4eb9),
       (0xc94,'source_create_checked',0x4eb9),
       (0x3291e,'submit',0x4ef9),
       (0x33442,'ocs_publish_queue',0x4ef9),
       (0x342c0,'ocs_publish_irq',0x4ef9),
       (0x33426,'ocs_publish_rotate',0x4ef9),
       (0x33348,'ocs_publish_clear',0x4ef9),
       (0x333b4,'ocs_publish_pixel',0x4ef9),
       (0x334b6,'ocs_publish_close',0x4ef9))


def build(out,option,exit_probe=False,changed="off", clock=False, prediction=False, intro=False, math_fast=False, public=False):
    math_fast = math_fast or public
    hooks=HOOKS+(((0x16992,'exit_probe_entry',0x4eb9),(0x18d14,'view_probe_entry',0x4ef9)) if exit_probe else ())
    if changed != 'off': hooks+=((0x3250c,'ocs_changed_borrow',0x4ef9),)
    native=dict(NATIVE)
    intro = intro or math_fast
    prediction = prediction or intro
    clock = clock or prediction
    if clock:
        from ocs_clock_source import NATIVE as clock_native, HOOKS as clock_hooks, MODALS, NOPS
        native.update(clock_native)
        hooks+=clock_hooks+tuple((off,'ocs_clock_modal_'+name,0x4ef9) for off,_,name,_ in MODALS)
    if prediction:
        from ocs_prediction_source import HOOKS as prediction_hooks, NOPS as prediction_nops
        hooks+=prediction_hooks
        native.update(OCS_PAD=0x33f24,OCS_KEYS=0x34606,OCS_GUN_RETURN=0xc226)
    if intro:
        from ocs_intro_source import NATIVE as intro_native, HOOKS as intro_hooks
        native.update(intro_native);hooks+=intro_hooks
    if public:
        hooks+=tuple((off,'cinematic_background',0x4eb9) for off in (0x1d0f2,0x1d10e,0x1d222,0x1d23e))
        native['OCS_CINEMATIC_DRAW']=0x2f9a6
    if math_fast:
        hooks+=((0x2adb6,'ocs_multiply',0x4ef9),
                (0x2b6d4,'ocs_distance_ratio',0x4ef9),
                (0x2b950,'ocs_radius',0x4ef9),
                (0x1574e,'ocs_collision_pair',0x4ef9))
        native.update(OCS_RATIO_RETURN=0x2b6f4,OCS_RADIUS=0x2b950,OCS_COLLISION_RESULT=0x1578e)
    original=(ROOT/ocs.SLAVE).read_bytes()
    require(hashlib.sha256(original).hexdigest()==SLAVE_SHA,'changed original slave')
    game=(ROOT/ocs.GAME).read_bytes();guard_game(game)
    (out/'original.bin').write_bytes(original[32:-4])
    prefix=f' section code,code\n org 0\nslave:\n incbin "{out}/original.bin"\n'
    equates='\n'.join(f'{n} equ ${0xf0000000+x:x}' for n,x in native.items())
    text=prefix+equates+f'''
install:
 movea.l a3,a0
 movea.l d7,a1
 jsr $74(a2)
 movem.l d0-d7/a0-a6,-(sp)
 lea slave+$1302(pc),a0
 cmpa.l a0,a3
 bne.w install_done
 move.l d7,d6
 lsl.l #2,d6
 addq.l #4,d6
 lea game_base(pc),a0
 move.l d6,(a0)
 lea guards(pc),a0
guard_loop:
 move.l (a0)+,d0
 bmi.s guards_done
 movea.l d6,a5
 adda.l d0,a5
 move.w (a0)+,d1
 cmp.w (a5)+,d1
 bne.w wrong_revision
 move.w (a0)+,d0
 move.l (a0)+,d1
 tst.w d0
 beq.s compare_guard
 add.l d6,d1
compare_guard:
 cmp.l (a5),d1
 bne.w wrong_revision
 bra.s guard_loop
guards_done:
 lea native_fixups(pc),a0
 lea slave(pc),a1
fixup:
 move.l (a0)+,d0
 bmi.s fixup_done
 movea.l a1,a5
 adda.l d0,a5
 move.l (a5),d1
 andi.l #$0fffffff,d1
 add.l d6,d1
 move.l d1,(a5)
 bra.s fixup
fixup_done:
 movea.l d6,a0
 adda.l #$342a8,a0
 move.l (a0),d0
 addi.l #$800,d0
 lea ocs_game_a4(pc),a0
 move.l d0,(a0)
 ; Unknown clocks remain native automatically. Explicit CPU is a build option.
 moveq #{OPTIONS[option]},d0
 movea.l 4.w,a0
 move.w 296(a0),d1
 moveq #0,d4
 btst #0,d1
 beq.s cpu020
 moveq #10,d4
cpu020:
 btst #1,d1
 beq.s cpu030
 moveq #20,d4
cpu030:
 btst #2,d1
 beq.s cpu040
 moveq #30,d4
cpu040:
 btst #3,d1
 beq.s cpu060
 moveq #40,d4
cpu060:
 btst #7,d1
 beq.s cpu_ready
 moveq #60,d4
cpu_ready:
 move.l d4,d1
 moveq #0,d2
 moveq #0,d3
 lea slave(pc),a0
 cmpa.l #$200000,a0
 bcs.s select_backend
 lea payload_end(pc),a0
 cmpa.l #$a00000,a0
 bhi.s select_backend
 moveq #7,d3
select_backend:
 bsr.w ocs_backend_choose
 lea ocs_requested_backend(pc),a0
 move.l d0,(a0)
 lea hooks(pc),a0
 lea slave(pc),a1
hook_loop:
 move.l (a0)+,d0
 bmi.s hooks_done
 movea.l d6,a5
 adda.l d0,a5
 move.w (a0)+,(a5)+
 move.l (a0)+,d0
 add.l a1,d0
 move.l d0,(a5)
 bra.s hook_loop
hooks_done:
 bsr.w slave+$ee8
install_done:
 movem.l (sp)+,d0-d7/a0-a6
 rts

display_create_checked:
 move.w 6(sp),-(sp)
 move.w 6(sp),-(sp)
 bsr.w ocs_display_create
 addq.l #4,sp
 tst.l d0
 beq.w memory_failure
 rts

source_create_checked:
 move.l 8(sp),-(sp)
 move.l 8(sp),-(sp)
 bsr.w ocs_source_create
 addq.l #8,sp
 tst.l d0
 beq.w memory_failure
 rts

submit:
 movem.l d0-d7/a0-a6,-(sp)
 jsr OCS_WAIT
 move.l ocs_source_backend(pc),d0
 beq.s native_submit
 move.l OCS_STAMP,d0
wait_field:
 cmp.l -$800(a4),d0
 beq.s wait_field
 movea.l OCS_CONVERSION+8,a0
 movea.l 64(sp),a2
 movea.l $1c(a2),a1
 moveq #0,d0
 moveq #0,d1
 move.w (a2),d0
 move.w 2(a2),d1
 move.l ocs_source_backend(pc),d2
 cmpi.l #2,d2
 beq.s convert_long
 bsr.w ocs_c2p_word
 bra.s converted
convert_long:
 bsr.w ocs_c2p_long
converted:
 tst.l d0
 bne.w contract_failure
 jsr OCS_COMPLETE
 movem.l (sp)+,d0-d7/a0-a6
 rts
native_submit:
 movem.l (sp)+,d0-d7/a0-a6
 movem.l d2-d7/a2-a6,-(sp)
 jmp OCS_SUBMIT_BODY
wrong_revision:
 pea 9.w
 movea.l slave+$f24(pc),a0
 jmp (a0)
memory_failure:
 pea memory_message(pc)
 bra.s abort_message
contract_failure:
 pea contract_message(pc)
abort_message:
 pea 43.w
 movea.l slave+$f24(pc),a0
 jmp (a0)
memory_message: dc.b "OCS display allocation failed",0
contract_message: dc.b "OCS CPU conversion contract failed",0
 even
game_base: dc.l 0
'''+(ROOT/'whdload/ocs_memory.s').read_text()+'\n'+(ROOT/'whdload/ocs_publication.s').read_text()+'\n'+backend_source()+'\n'+converter_source(candidates())
    if clock:
        from ocs_clock_source import source as clock_source
        if prediction:
            # Place the shared contact unit before the clock so the existing
            # clock/intro/exhaust calls retain their 68000 PC-relative reach.
            from ocs_prediction_source import field_source
            from shared_cpu import preamble
            text+='\n'+preamble(ROOT,'68000')+field_source(ROOT)
            text+='\n'+clock_source(ROOT,game).replace(preamble(ROOT,'68000'),'')
        else:
            text+='\n'+clock_source(ROOT,game)
        if prediction:
            from ocs_prediction_source import source as prediction_source
            from shared_cpu import select
            text+='\n'+prediction_source(ROOT)+'\n'+select((ROOT/'whdload/ocs_prediction.s').read_text(),'68000')
            text=prediction_clock(text)
            if intro:
                from ocs_intro_source import source as intro_source, integrate
                text=integrate(text)+intro_source(ROOT)
            text+=select((ROOT/'whdload/ocs_exhaust.s').read_text(),'68000')
            from ocs_prediction_source import external_source
            text+=external_source(ROOT)
        # Extra overwritten words are separately guarded before any mutation.
        nops=NOPS+(prediction_nops if prediction else ())+tuple(at for off,width,_,_ in MODALS for at in range(off+6,off+width,2))
        checks=''.join(f' movea.l d6,a5\n adda.l #${off:x},a5\n cmpi.w #${int.from_bytes(game[44+off:46+off],"big"):x},(a5)\n bne.w wrong_revision\n' for off in nops if off not in (0x878,0x87a,0x9c2,0x9c4))
        for off in (0x878,0x9c2):
            checks+=f' movea.l d6,a5\n adda.l #${off:x},a5\n move.l d6,d0\n addi.l #${int.from_bytes(game[44+off:48+off],"big"):x},d0\n cmp.l (a5),d0\n bne.w wrong_revision\n'
        text=text.replace('guards_done:\n','guards_done:\n'+checks)
        text=text.replace('hooks_done:\n','hooks_done:\n'+''.join(f' movea.l d6,a5\n adda.l #${off:x},a5\n move.w #$4e71,(a5)\n' for off in nops))
    if math_fast:
        text+='\n'+(ROOT/'whdload/ocs_math.s').read_text()
        text+='\nocs_multiply_native:\n dc.b '+','.join(f'${v:02x}' for v in game[44+0x2adb6:44+0x2adbc])+'\n jmp $f002adbc\n'
        text+='\nocs_radius_native:\n dc.b '+','.join(f'${v:02x}' for v in game[44+0x2b950:44+0x2b956])+'\n jmp $f002b956\n'
    if changed != 'off':
        text=text.replace(' lea payload_end(pc),a0',
                          ' lea payload_end(pc),a0\n adda.l #128000,a0')
        # Equal-sized full/blocks controls include identical history reservation.
        # Invalidation is task-side, after the C5 drain, before native writers.
        text=text.replace('        bsr.w   ocs_publish_drain\n',
                          '        bsr.w   ocs_publish_drain\n        bsr.w ocs_changed_invalidate\n')
        if changed == 'blocks':
            text=text.replace(' bsr.w ocs_c2p_word', ' bsr.w ocs_changed_word')
            text=text.replace(' bsr.w ocs_c2p_long', ' bsr.w ocs_changed_long')
        text+='\n'+(ROOT/'whdload/ocs_changed.s').read_text()+'''
; Native O:32504 lends inactive display storage to general scratch consumers.
; Its six displaced bytes follow the original final-conversion/field wait.
ocs_changed_borrow:
 bsr.w ocs_publish_drain
 bsr.w ocs_changed_invalidate
 move.l 8(a0),d0
 move.l (a0),d1
 jmp OCS_SCRATCH_BODY
'''

    if exit_probe:
        text+='''
exit_probe_entry:
 move.l d0,-(sp)
 move.l exit_probe_trigger(pc),d0
 bne.s .exit
 move.l (sp)+,d0
 jmp OCS_INPUT
.exit:
 move.l (sp)+,d0
 jsr OCS_PRIMARY_CLOSE
 jsr OCS_DISPLAY_FREE
exit_probe_done:
 bra.s exit_probe_done
exit_probe_trigger: dc.l 0
; Diagnostic task-context view request; simulator key dispatch disables F1-F4.
view_probe_entry:
 movem.l d2-d4,-(sp)
 move.l view_probe_request(pc),d0
 beq.s .native
 subq.w #1,d0
 clr.w -(sp)
 move.w d0,-(sp)
 jsr OCS_VIEW_CHANGE
 addq.l #4,sp
 lea view_probe_request(pc),a0
 clr.l (a0)
.native:
 jsr OCS_INPUT_PREPARE
 jmp OCS_INPUT_BODY
view_probe_request: dc.l 0
'''
    if public:
        text=text.replace(' move.l d7,d6\n',
                          ' bsr.w ocs_option_gate\n tst.l d0\n beq.w install_done\n move.l d7,d6\n',1)
        # Keep option code/data in PC-relative range of the startup seam.
        config=original[32+0xf81:].split(b'\0',1)[0].rstrip(b';')
        config+=b';C5:B:Enhanced framerate (68020+Fast RAM);\0'
        options=(ROOT/'whdload/ocs_options.s').read_text()
        options+='\nocs_public_info: dc.b "2.0b (19.10.2026)",10,"Original slave: Psygore",10,"Improvements: Vesuri",0\nocs_public_version: dc.b "$VER: WingCommander 2.0b (19.10.2026)",0\n even\n'
        options+='\nocs_public_config: dc.b '+','.join(str(x) for x in config)+'\n even\n'
        text=text.replace('display_create_checked:',options+'\ndisplay_create_checked:',1)
    if public:
        from modal_source import source as modal_source
        from opening_source import source as opening_source
        text=text.replace('display_create_checked:',opening_source(ROOT,'ocs')+'\ndisplay_create_checked:',1)
        text=text.replace('guards_done:\n','guards_done:\n movea.l d6,a0\n bsr.w opening_guard\n lea install(pc),a1\n adda.l #modal_guard-install,a1\n jsr (a1)\n',1)
        text=text.replace('hooks_done:\n','hooks_done:\n movea.l d6,a0\n bsr.w opening_install\n lea install(pc),a1\n adda.l #modal_install-install,a1\n jsr (a1)\n',1)
    if public:
        text+=(ROOT/'whdload/cinematic_background.s').read_text().replace(
            '        CINEMATIC_DRAW','        jmp OCS_CINEMATIC_DRAW')
    if public:
        # The enlarged payload needs a long address calculation for this call.
        text+=modal_source(ROOT,'ocs').replace('        bsr.w timing_rate', '        lea modal_room_begin(pc),a0\n        adda.l #timing_rate-modal_room_begin,a0\n        jsr (a0)')
    if intro:
        # The appended D4 payload puts startup tables beyond d16(PC).
        for label in ('guards','native_fixups','payload_end','hooks'):
            text=text.replace(f' lea {label}(pc),a0', f' lea install(pc),a0\n adda.l #{label}-install,a0')
    # Resolve native operands at startup. Fixups are constructed from unique
    # sentinel values, then checked as operands in the generated build listing.
    guards='\nguards:\n'
    for off,_,_ in hooks:
        raw=game[44+off:44+off+6]
        guards+=f' dc.l ${off:x}\n dc.w ${int.from_bytes(raw[:2],"big"):x},{int(int.from_bytes(raw[:2],"big") in (0x4eb9,0x4ef9))}\n dc.l ${int.from_bytes(raw[2:],"big"):x}\n'
    guards+=' dc.l -1\n'
    tables=guards+'\nhooks:\n'+''.join(f' dc.l ${off:x}\n dc.w ${op:x}\n dc.l {label}-slave\n' for off,label,op in hooks)+' dc.l -1\nnative_fixups:\n'
    # First pass obtains positions; later tables cannot shift preceding code.
    history='ocs_changed_history: ds.b 128000\n' if changed != 'off' else ''
    probe,sy=assemble(out,'probe',text+tables+' dc.l -1\npayload_end:\n'+history)
    fixes=[]
    # D4 hook offsets can resemble sentinel operands across word boundaries;
    # never relocate table data. Preserve older controls byte for byte.
    for pos in range(TAIL,(sy["guards"] if intro else len(probe))-3,2):
        value=int.from_bytes(probe[pos:pos+4],'big')
        if 0xf0000000<=value<0xf0040000:fixes.append(pos)
    require(len(fixes)>=len(native)-5,'missing native fixups')
    payload,sy=assemble(out,'candidate',text+tables+''.join(f' dc.l ${x:x}\n' for x in fixes)+' dc.l -1\npayload_end:\n'+history)
    payload=bytearray(payload)
    require(payload[:TAIL]==original[32:-4],'original payload changed before patch')
    require(sy['install']-0x11c8<32768,'install trampoline out of range')
    payload[0x11c6:0x11ce]=struct.pack('>HhHH',0x6100,sy['install']-0x11c8,0x4e71,0x4e71)
    if public:
        require(sy['ocs_public_config'] < 65536, 'public configuration offset overflow')
        struct.pack_into('>H',payload,0x32,sy['ocs_public_config'])
        require(sy['ocs_public_info'] < 65536, 'public info offset overflow')
        struct.pack_into('>H',payload,0x28,sy['ocs_public_info'])
        # Normal campaign entry can fragment both native pools enough to
        # reject the 42511-byte side-cockpit image. Keep its native ownership
        # and cleanup, supplying one extra 64 KiB of game-pool headroom.
        require(payload[0x20:0x24] == struct.pack('>I',0xf0000),
                'unexpected original expansion request')
        require(payload[0x1fc:0x202] == bytes.fromhex('d9fc000b0000'),
                'unexpected original expansion-pool bound')
        struct.pack_into('>I',payload,0x20,0x100000)
        struct.pack_into('>I',payload,0x1fe,0xc0000)
    payload+=bytes((-len(payload))%4)
    blob=struct.pack('>8I',0x3f3,0,1,0,0,len(payload)//4,0x3e9,len(payload)//4)+payload+struct.pack('>I',0x3f2)
    (out/'WingCommander.Slave').write_bytes(blob)
    report=dict(variant='ocs',candidate=True,backend=option,bytes=len(blob),
                sha256=hashlib.sha256(blob).hexdigest(),symbols=sy,fixups=fixes,hooks=list(hooks),exit_probe=exit_probe,changed=changed,history_bytes=128000 if changed!='off' else 0,
                public_option=public,opening=public,
                version='2.0b' if public else None, release_date='19.10.2026' if public else None,
                expansion_bytes=0x100000 if public else 0xf0000,
                game_pool_bytes=0xc0000 if public else 0xb0000,
                workspace='native combined Chip allocation retained for fallback',
                live_validated=False,clock=clock,prediction=prediction,intro=intro,math_fast=math_fast)
    if public:
        from ocs_icon import enhanced_icon
        icon=(ROOT/'tmp/originals/ocs/WingCommander/WingCommander.info').read_bytes()
        (out/'WingCommander.info').write_bytes(enhanced_icon(icon))
        (out/'ReadMe').write_bytes((ROOT/'release/ReadMe.OCS').read_bytes())
    (out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def prediction_clock(text):
    # Keep the D2 control exactly reproducible; integrate D3 only when requested.
    text=text.replace('        bsr.w   ocs_publish_vblank',
                      '        bsr.w   ocs_publish_vblank\n        bsr.w ocs_input_record')
    text=text.replace('ocs_clock_rebase:\n','ocs_clock_rebase:\n        bsr.w ocs_prediction_rebase\n')
    text=text.replace('        bsr.w ocs_clock_tick\n        subq.w',
        '        lea timing_in_world(pc),a0\n        move.w #1,(a0)\n        bsr.w ocs_clock_tick\n        lea timing_in_world(pc),a0\n        clr.w (a0)\n        subq.w')
    text=text.replace('        jsr OCS_ATTACHMENTS', '        bsr.w ocs_exhaust_capture\n        jsr OCS_ATTACHMENTS')
    text=text.replace('ocs_clock_tick_done:', '        bsr.w ocs_prediction_snapshot\nocs_clock_tick_done:')
    text=text.replace('        jsr OCS_DRAW\n', '        bsr.w ocs_prediction_begin\n        jsr OCS_DRAW\n        bsr.w ocs_prediction_end\n')
    text=text.replace('        move.l ocs_clock_dirty(pc),d0\n        cmp.l',
        '        move.l a0,-(sp)\n        lea ocs_prediction_fast(pc),a0\n        tst.w (a0)\n        movea.l (sp)+,a0\n        bne.s ocs_prediction_draw_ready\n        move.l ocs_clock_dirty(pc),d0\n        cmp.l',1)
    text=text.replace('        bsr.w ocs_clock_draw\n', 'ocs_prediction_draw_ready:\n        bsr.w ocs_clock_draw\n',1)
    a=text.index('.bounded:\n',text.index('ocs_clock_batch:'));b=text.index('        tst.l d0\n',a)
    text=text[:a]+'.bounded:\n        bsr.w ocs_input_take\n        tst.w d0\n        beq.w .done\n        bsr.w ocs_prediction_field\n        move.l ocs_input_sample(pc),d0\n        move.l ocs_clock_hz(pc),d1\n        moveq #1,d2\n        lea ocs_clock_state(pc),a0\n        bsr.w timing_advance\n'+text[b:]
    a=text.index('ocs_clock_batch:');b=text.index('ocs_clock_rebase:',a)
    text=text[:a]+text[a:b].replace('jsr OCS_FLIGHT_INPUT','bsr.w ocs_prediction_input')+text[b:]
    # Never present a forecast before its named target. Late service remains
    # measured lateness, not permission to extrapolate past the shared bound.
    text=text.replace('ocs_publish_queue:\n', 'ocs_publish_queue:\n        bsr.w ocs_prediction_completed\n')
    text=text.replace('        move.l  d0,(a1)\n        lea     ocs_pending(pc),a1',
        '        move.l a0,-(sp)\n        lea ocs_prediction_queued(pc),a0\n        move.w (a0),-(sp)\n        clr.w (a0)\n        tst.w (sp)+\n        movea.l (sp)+,a0\n        beq.s .target_ready\n        cmp.l release_render_time(pc),d0\n        bpl.s .target_ready\n        move.l release_render_time(pc),d0\n.target_ready:\n        move.l d0,(a1)\n        lea     ocs_pending(pc),a1')
    # Kalms components reopen the same section; keep a single origin so vasm
    # does not treat earlier absolute symbols as literal PC displacements.
    import re
    text=re.sub(r'^\s*section\s+code,code\s*$', '', text, flags=re.M)
    return ' section code,code\n'+text

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    p.add_argument('--backend',choices=tuple(OPTIONS),default=None)
    p.add_argument('--public',action='store_true',help='guard all enhancements with CUSTOM5 and 68020/true Fast; emit enabled icon')
    p.add_argument('--exit-probe',action='store_true',help='diagnostic-only native teardown and view-change triggers')
    p.add_argument('--changed',choices=('off','full','blocks'),default='off',help='C6 opt-in history candidate or equal-reservation full control')
    p.add_argument('--clock',action='store_true',help='D2 opt-in 10 Hz flight clock')
    p.add_argument('--prediction',action='store_true',help='D3 opt-in field input and bounded prediction')
    p.add_argument('--intro',action='store_true',help='D4 OCS title/credits clock and prediction (implies --prediction)')
    p.add_argument('--math-fast',action='store_true',help='E1 exact native arithmetic shortcuts (implies --intro)')
    a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
    r=build(out,a.backend or ('cpu' if a.public else 'auto'),a.exit_probe,a.changed,a.clock,a.prediction,a.intro,a.math_fast,a.public);print(r['bytes'],r['sha256'])

if __name__=='__main__':main()
