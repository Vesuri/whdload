"""Pinned OCS clock integration; generated displaced native bytes stay in tmp/."""
from shared_cpu import preamble, select, unit

NATIVE = dict(OCS_WORLD=0x2be, OCS_FLIGHT_INPUT=0x18d14,
 OCS_FLIGHT_EXIT=0x6c4, OCS_GEOMETRY=0x290fa, OCS_DEBRIS=0x27cfa,
 OCS_FLAMES=0x281c0, OCS_ATTACHMENTS=0x2837a, OCS_ASTEROIDS=0x9618,
 OCS_MESSAGE=0x2018, OCS_TARGET=0x3908, OCS_FAULTS=0xacfa,
 OCS_DRAW=0x512, OCS_SYSTEMS=0x4460, OCS_SYSTEMS_BODY=0x4464,
 OCS_SORT=0x2ba2c, OCS_RASTER=0x2bab4, OCS_SCENE=0x28548,
 OCS_SIM_BODY=0x538, OCS_SELECTION_READY=0x4898, OCS_SELECTION_WAIT=0x49d0)
HOOKS = ((0x694,'ocs_clock_loop',0x4ef9),
 (0x322,'ocs_clock_scene_draw',0x4eb9),
 (0x330,'ocs_clock_asteroids_draw',0x4eb9),
 (0x51c,'ocs_clock_message_draw',0x4eb9),
 (0x532,'ocs_clock_sim_draw',0x4ef9),
 (0x43a,'ocs_clock_score_draw',0x4eb9),
 (0x636a,'ocs_clock_emission',0x4eb9),
 (0x4464,'ocs_clock_faults_draw',0x4eb9),
 (0x4890,'ocs_clock_selection',0x4ef9))
NOPS = (0x440,0x6370,0x4896)
# Modal calls have no arguments except the one-word sound/options menu.
MODALS = ((0x872,10,'pause',0),(0xf56,8,'autopilot',0),
          (0x9bc,10,'options',2),(0x18c6e,6,'keywait',0))


def source(root, game):
    text=(root/'whdload/ocs_clock.s').read_text()
    # Reuse the established beam classification and scheduler, selecting the
    # previously checked 68000 arithmetic expansions. No CD32 game ABI enters.
    shared=(root/'whdload/timing.s').read_text()
    rate=shared[shared.index('timing_rate:'):shared.index('; Ordinary loop consumes')]
    text += '\n'+rate+'\n'+unit(root,'timing_clock','68000')
    for off,width,name,arg in MODALS:
        original=bytearray(game[44+off:44+off+width])
        # The two absolute JSR prologues need the usual native startup fixup.
        if name in ('pause','options'):
            original[6:10]=(int.from_bytes(original[6:10],'big')+0xf0000000).to_bytes(4,'big')
        text+=f'''
ocs_clock_modal_{name}:
        bsr.w ocs_clock_suspend
'''
        if arg: text+='        move.w 4(sp),-(sp)\n'
        text+=f'        bsr.w ocs_clock_original_{name}\n'
        if arg:text+='        addq.l #2,sp\n'
        text+='        bra.w ocs_clock_resume\n'
        text+=f'ocs_clock_original_{name}:\n dc.b '+','.join(f'${b:02x}' for b in original)+'\n'
        text+=f'        jmp ${0xf0000000+off+width:x}\n'
    text+='''
ocs_clock_suspend:
        movem.l d0/a0,-(sp)
        lea ocs_clock_modal_depth(pc),a0
        addq.w #1,(a0)
        cmpi.w #1,(a0)
        bne.s .done
        lea ocs_clock_modal_active(pc),a0
        move.w ocs_clock_active(pc),(a0)
        lea ocs_clock_active(pc),a0
        clr.w (a0)
        bsr.w ocs_clock_rebase
.done:
        movem.l (sp)+,d0/a0
        rts
ocs_clock_resume:
        movem.l d0/a0,-(sp)
        WC_PUSH_CCR
        lea ocs_clock_modal_depth(pc),a0
        subq.w #1,(a0)
        bne.s .done
        bsr.w ocs_clock_rebase
        lea ocs_clock_active(pc),a0
        move.w ocs_clock_modal_active(pc),(a0)
.done:
        move.w (sp)+,ccr
        movem.l (sp)+,d0/a0
        rts
ocs_clock_modal_depth: dc.w 0
ocs_clock_modal_active: dc.w 0
'''
    return preamble(root,'68000')+'\n'+select(text,'68000')
