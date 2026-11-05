"""Add road-relative actor state to the unchanged field-scheduled lap replay."""
import struct
import replay_a
original = replay_a.snapshot
def snapshot(s):
    result = original(s)
    actor = replay_a.read_bytes(s, 0xa5d60, 0x80)
    result.update(road_center=struct.unpack_from('>h',actor,0x36)[0],
                  road_fraction=struct.unpack_from('>H',actor,0x38)[0],
                  acceleration=struct.unpack_from('>h',actor,0x14)[0],
                  gear=struct.unpack_from('>H',actor,0x18)[0],
                  displacement=struct.unpack_from('>I',actor,0x26)[0])
    result['player_raw']=actor.hex()
    result['road_relative']=result['road_center']-result['lateral']
    return result
route_original=replay_a.route
def route(s):
    result=route_original(s)
    (s.out/'steering-code.txt').write_text(s.cmd('disassemble 0x8b8c0,0x8b9a8'))
    return result
replay_a.route=route
replay_a.snapshot = snapshot
replay_a.main()
