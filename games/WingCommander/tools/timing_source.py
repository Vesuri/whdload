"""Generate pinned-input guards for the English timing adapter in ignored builds."""
import hashlib
import struct
from shared_cpu import unit, preamble


def source(root, buffered=False, *, variant):
    from variants import get, timing_hooks, assembly_definitions
    v = get(variant)
    patches = timing_hooks(v, buffered)
    game = (root / v.GAME).read_bytes()
    if hashlib.sha256(game).hexdigest() != v.GAME_SHA:
        raise ValueError('changed English executable')
    offset, size, _ = v.HUNKS[0]
    code = game[offset:offset+size]
    lines=[preamble(root,v.CPU),assembly_definitions(v),unit(root, 'timing', v.CPU),unit(root, 'timing_clock', v.CPU),unit(root, 'timing_player', v.CPU),unit(root, 'timing_input', v.CPU),unit(root, 'timing_presentation', v.CPU),unit(root, 'timing_scene', v.CPU),'timing_install:']
    if buffered:
        lines.insert(-1,unit(root, 'timing_intro', v.CPU))
        lines.insert(-1,unit(root, 'timing_translation', v.CPU))
        lines.insert(-1,unit(root, 'timing_projectiles', v.CPU))
        lines.insert(-1,unit(root, 'timing_scene_slots', v.CPU))
        lines.insert(-1,unit(root, 'view_regions', v.CPU))
    for offset,_,_ in patches:
        word=struct.unpack_from('>H',code,offset)[0]
        lines += [f'\tcmpi.w #${word:04x},${offset:x}(a0)','\tbne.w timing_bad']
        if word==0x4eb9:
            target=struct.unpack_from('>I',code,offset+2)[0]
            lines += ['\tmove.l a0,d0',f'\taddi.l #${target:x},d0',
                      f'\tcmp.l ${offset+2:x}(a0),d0','\tbne.w timing_bad']
        else:
            width=8 if offset in v.WIDE_GUARDS else 6
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
    if buffered: lines += ['\tmove.w #$4e71,$1fe4a(a0)']
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
