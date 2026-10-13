"""Generate pinned-input guards for the English timing adapter in ignored builds."""
import hashlib
import struct


def source(root):
    game=(root/'tmp/originals/cd32/WingCommanderCD32/data/wing.english').read_bytes()
    if hashlib.sha256(game).hexdigest()!='093505483aed4c9dbd1b97484c3336e92fdb156be9c15a67ed0199bd4dade657':
        raise ValueError('changed English executable')
    code=game[0x2c:0x2c+0x35ea4]
    patches=[(0x698,'timing_loop',0x4ef9),(0x176,'timing_pause',0x4eb9),
             (0x24c,'timing_pause',0x4eb9),(0x2571c,'timing_pause',0x4eb9),
             (0x18eee,'timing_throttle_gate',0x4eb9),(0x18f00,'timing_throttle_gate',0x4eb9),
             (0x18f3a,'timing_fire_gate',0x4eb9),(0x7bc2,'timing_world_rotation',0x4eb9)]
    lines=[(root/'whdload/timing.s').read_text(),(root/'whdload/timing_clock.s').read_text(),(root/'whdload/timing_player.s').read_text(),'timing_install:']
    for offset,_,_ in patches:
        word=struct.unpack_from('>H',code,offset)[0]
        lines += [f'\tcmpi.w #${word:04x},${offset:x}(a0)','\tbne.w timing_bad']
        if word==0x4eb9:
            target=struct.unpack_from('>I',code,offset+2)[0]
            lines += ['\tmove.l a0,d0',f'\taddi.l #${target:x},d0',
                      f'\tcmp.l ${offset+2:x}(a0),d0','\tbne.w timing_bad']
        else:
            width=8 if offset==0x7bc2 else 6
            for at in range(offset+2,offset+width,2):
                value=struct.unpack_from('>H',code,at)[0]
                lines += [f'\tcmpi.w #${value:04x},${at:x}(a0)','\tbne.w timing_bad']
    lines += ['\tlea $6c8(a0),a1','\tlea timing_exit(pc),a3','\tmove.l a1,(a3)']
    for offset,label,opcode in patches:
        lines += [f'\tmove.w #${opcode:04x},${offset:x}(a0)',f'\tlea {label}(pc),a1',f'\tmove.l a1,${offset+2:x}(a0)']
    lines += ['\tmove.w #$4e71,$7bc8(a0)','\trts','\tcnop 0,4']
    return '\n'.join(lines)
