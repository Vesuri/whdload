"""Observe native rank inputs without redefining existing A4 comparisons."""
import struct
import replay_a
original = replay_a.snapshot

def snapshot(s):
    result = original(s)
    def inactive(address):
        raw = replay_a.read_bytes(s,address,66)
        count = struct.unpack_from('>H',raw)[0]
        if count > 16: raise RuntimeError(f'invalid inactive count {count}')
        return [hex(struct.unpack_from('>I',raw,2+4*i)[0]) for i in range(count)]
    ahead, behind = inactive(0x90946), inactive(0x90988)
    positions = {a['address']:a['position'] for a in result['actors']}
    native_rank = 1 + sum(p != '0xa5de0' for p in ahead)
    native_rank += sum(p != '0xa5de0' and positions.get(p,0)>result['position'] for p in result['active_actors'][1:])
    packed = result['rank']
    result['rank_audit'] = dict(ahead=ahead,behind=behind,reconstructed=native_rank,
        displayed=10*(packed>>4)+(packed&15),stored_position_rank=result['order'].index('0xa5d60')+1)
    return result
replay_a.snapshot = snapshot
if __name__ == "__main__": replay_a.main()
