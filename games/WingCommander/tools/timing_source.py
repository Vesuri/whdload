"""Generate pinned-input guards for the English timing adapter in ignored builds."""
import hashlib
import struct


def source(root, buffered=False):
    game=(root/'tmp/originals/cd32/WingCommanderCD32/data/wing.english').read_bytes()
    if hashlib.sha256(game).hexdigest()!='093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657':
        raise ValueError('changed English executable')
    code=game[0x2c:0x2c+0x35ea4]
    patches=[(0x28c86,'timing_debris_draw',0x4ef9),(0x698,'timing_loop',0x4ef9),(0x878,'timing_pause',0x4ef9),(0x101c,'timing_autopilot',0x4ef9),
             (0x18eee,'timing_throttle_gate',0x4eb9),(0x18f00,'timing_throttle_gate',0x4eb9),
             (0x18f3a,'timing_fire_gate',0x4eb9),(0x7bc2,'timing_world_rotation',0x4eb9),
             (0x34188,'timing_record_input',0x4eb9),(0x1934c,'timing_pad_read',0x4eb9),
             (0x18c6a,'timing_keys_read',0x4eb9),(0x19380,'timing_key_command',0x4eb9),
             (0x65f4,'timing_emission_clock',0x4eb9),(0x51a,'timing_message_draw',0x4eb9),(0x46ea,'timing_systems_draw',0x4eb9),
             (0x530,'timing_sim_draw',0x4ef9),(0x438,'timing_sim_score_draw',0x4eb9),(0x3b8e,'timing_target_draw',0x4ef9),(0x4b16,'timing_selection',0x4ef9),
             (0x435c,'timing_portrait_clock',0x4eb9),(0x43ee,'timing_portrait_random',0x4eb9)]
    if buffered:
        patches=[(off,'release_input_vblank' if off==0x34188 else label,op) for off,label,op in patches]
        patches += [(0x306,'view_clear',0x4eb9),(0xc4c,'view_compose',0x4eb9),(0x2b648,'timing_scene_allocate',0x4ef9),(0x807a,'translation_velocity',0x4ef9),(0x80b6,'translation_position',0x4ef9),(0x3378e,'release_publish',0x4ef9),(0x337ea,'release_teardown',0x4ef9)]
    lines=[(root/'whdload/timing.s').read_text(),(root/'whdload/timing_clock.s').read_text(),(root/'whdload/timing_player.s').read_text(),(root/'whdload/timing_input.s').read_text(),(root/'whdload/timing_presentation.s').read_text(),(root/'whdload/timing_scene.s').read_text(),'timing_install:']
    if buffered:
        lines.insert(-1,(root/'whdload/timing_translation.s').read_text())
        lines.insert(-1,(root/'whdload/timing_scene_slots.s').read_text())
        lines.insert(-1,(root/'whdload/view_regions.s').read_text())
    for offset,_,_ in patches:
        word=struct.unpack_from('>H',code,offset)[0]
        lines += [f'\tcmpi.w #${word:04x},${offset:x}(a0)','\tbne.w timing_bad']
        if word==0x4eb9:
            target=struct.unpack_from('>I',code,offset+2)[0]
            lines += ['\tmove.l a0,d0',f'\taddi.l #${target:x},d0',
                      f'\tcmp.l ${offset+2:x}(a0),d0','\tbne.w timing_bad']
        else:
            width=8 if offset in (0x28c86,0x7bc2,0x878,0x65f4,0x4b16,0x101c,0x438,0x3b8e,0x3378e) else 6
            for at in range(offset+2,offset+width,2):
                value=struct.unpack_from('>H',code,at)[0]
                lines += [f'\tcmpi.w #${value:04x},${at:x}(a0)','\tbne.w timing_bad']
    lines += ['\tlea $28c8e(a0),a1','\tlea timing_debris_resume(pc),a3','\tmove.l a1,(a3)']
    lines += ['\tmove.l -4(a0),d0','\tlsl.l #2,d0','\taddq.l #4,d0','\tlea timing_data(pc),a1','\tmove.l d0,(a1)']
    lines += ['\tlea $3b96(a0),a1','\tlea timing_target_resume(pc),a3','\tmove.l a1,(a3)']
    lines += ['\tlea $1024(a0),a1','\tlea timing_autopilot_resume(pc),a3','\tmove.l a1,(a3)']
    lines += ['\tlea $880(a0),a1','\tlea timing_pause_resume(pc),a3','\tmove.l a1,(a3)']
    lines += ['\tlea $6c8(a0),a1','\tlea timing_exit(pc),a3','\tmove.l a1,(a3)']
    for offset,label,opcode in patches:
        lines += [f'\tmove.w #${opcode:04x},${offset:x}(a0)',f'\tlea {label}(pc),a1',f'\tmove.l a1,${offset+2:x}(a0)']
    lines += ['\tmove.w #$4e71,$28c8c(a0)','\tmove.w #$4e71,$43e(a0)','\tmove.w #$4e71,$3b94(a0)','\tmove.w #$4e71,$1022(a0)','\tmove.w #$4e71,$65fa(a0)','\tmove.w #$4e71,$4b1c(a0)','\tmove.w #$4e71,$7bc8(a0)','\tmove.w #$4e71,$87e(a0)','\trts',
              'timing_pause_original:','\tdc.b '+','.join(f'${x:02x}' for x in code[0x878:0x880]),
              '\tmove.l timing_pause_resume(pc),-(sp)','\trts','\tcnop 0,4','timing_pause_resume: dc.l 0']
    lines += ['timing_autopilot_original:','\tdc.b '+','.join(f'${x:02x}' for x in code[0x101c:0x1024]),'\tmove.l timing_autopilot_resume(pc),-(sp)','\trts','\tcnop 0,4','timing_autopilot_resume: dc.l 0']
    lines += ['timing_target_original:','\tdc.b '+','.join(f'${x:02x}' for x in code[0x3b8e:0x3b96]),'\tmove.l timing_target_resume(pc),-(sp)','\trts','\tcnop 0,4','timing_target_resume: dc.l 0']
    lines += ['timing_debris_original:','\tdc.b '+','.join(f'${x:02x}' for x in code[0x28c86:0x28c8e]),'\tmove.l timing_debris_resume(pc),-(sp)','\trts','\tcnop 0,4','timing_debris_resume: dc.l 0']
    if buffered:
        lines += ['release_publish_native:', '\tmove.l timing_game(pc),a0', '\tlea $331f4(a0),a0',
                  '\tmove.w $1c(a0),-(sp)', '\tmove.l release_publish_resume(pc),-(sp)', '\trts',
                  'release_teardown_native:', '\tmove.l a2,-(sp)', '\tmove.l timing_game(pc),a2',
                  '\tlea $331f4(a2),a2', '\tmove.l release_teardown_resume(pc),-(sp)', '\trts',
                  '\tcnop 0,4', 'release_publish_resume: dc.l 0', 'release_teardown_resume: dc.l 0']
        at=lines.index('timing_install:')+1
        lines[at:at]=['\tlea $33796(a0),a1','\tlea release_publish_resume(pc),a3','\tmove.l a1,(a3)',
                     '\tlea $337f0(a0),a1','\tlea release_teardown_resume(pc),a3','\tmove.l a1,(a3)']
    return '\n'.join(lines)
