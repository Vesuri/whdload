#!/usr/bin/env python3
"""D2 native equivalence checks; Unicorn is a correctness instrument only."""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from cd32_runtime import ROOT
from timing_audit_check import CPU

S = 0x180000


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--run', type=Path, default=ROOT/'tmp/phase10-isolated-turn-ntsc')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    out = a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('new tmp output required')
    meta = json.loads((a.run/'result.json').read_text())
    memory = (a.run/'end-fast.bin').read_bytes()
    blob = (a.build/'payload.bin').read_bytes()
    sy = {n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$', (a.build/'slave.lst').read_text(), re.M)}
    counts = dict(geometry_pairs=0, guarded_edges=0, slot_roundtrips=0, allocator_pairs=0, geometry_boundaries=0, unchanged_queues=0, guarded_transitions=0)
    sources = {}
    history_negative = False
    for model in (2,4):
        c = CPU(memory,meta,model)
        ref = CPU(memory,meta,model)
        c.write(S,blob)
        def put(n,v):c.write(S+sy[n],struct.pack('>H',v))
        def run(n):c.run(S+sy[n]-c.code)
        c.write(S+sy['timing_game'],struct.pack('>I',c.code))
        c.write(c.code+0x2b648,struct.pack('>HI',0x4ef9,S+sy['timing_scene_allocate']))
        for stem in meta['scene_samples']:
            initial = (a.run/(stem+'-restored.bin')).read_bytes()
            sources[stem] = hashlib.sha256(initial).hexdigest()
            # Native double rebuild is the oracle; compare the whole data hunk.
            c.write(c.data,initial)
            run('timing_scene_geometry');run('timing_scene_geometry')
            want = c.read(c.data,0xfda0)
            c.write(c.data,initial);put('timing_pad_count',0)
            run('timing_edge_geometry')
            assert c.read(c.data,0xfda0)==initial, 'no-edge geometry not deferred'
            run('timing_scene_geometry')
            history_negative |= c.read(c.data,0xfda0)!=want
            run('timing_geometry_history')
            assert c.read(c.data,0xfda0)==want, ('geometry',model,stem)
            counts['geometry_pairs'] += 1
            # With a queued edge the first rebuild is retained. Mutate a pose
            # as an edge command could, then require the normal second rebuild.
            c.write(c.data,initial);put('timing_pad_count',1)
            pending=bytearray(initial[0xc6c8:0xc6d8]);pending[0]^=1
            c.write(S+sy['timing_pad_pending'],bytes(pending))
            run('timing_edge_geometry')
            first = c.read(c.data,0xfda0)
            c.write(c.data,initial);run('timing_scene_geometry')
            assert c.read(c.data,0xfda0)==first
            assert c.read(S+sy['timing_geometry_repeat'],2)==bytes(2)
            c.data_value(0x919a,'i',c.data_value(0x919a,'i')+1024)
            run('timing_scene_geometry');want=c.read(c.data,0xfda0)
            run('timing_geometry_history');assert c.read(c.data,0xfda0)==want
            counts['guarded_edges'] += 1
        assert history_negative, 'range-history negative control did not exercise a difference'
        # Native boundary classes and all four cockpit views. Seed old ranges
        # differently so a missing replay cannot pass through equal values.
        for view in range(4):
            c.reset();c.data_value(0x3896,'h',view)
            c.write(c.data+0x96fe+20,bytes(102))
            for slot,kind in ((10,1),(11,7),(12,-1),(60,1)):
                c.data_value(0x96fe+2*slot,'h',kind)
                c.data_value(0xa4dc+2*slot,'h',1234)
                c.data_value(0xa55c+2*slot,'h',4321)
            initial=c.read(c.data,0xfda0)
            run('timing_scene_geometry');run('timing_scene_geometry')
            want=c.read(c.data,0xfda0)
            c.write(c.data,initial);put('timing_pad_count',0)
            run('timing_edge_geometry');run('timing_scene_geometry');run('timing_geometry_history')
            assert c.read(c.data,0xfda0)==want, ('boundary geometry',model,view)
            counts['geometry_boundaries']+=1

        # Unchanged queued samples still execute the real edge dispatcher.
        # Compare its whole-data outcome between two rebuilds and one+history.
        for pad in (bytes(16), bytes([1])*16):
            c.reset();c.write(c.data+0xc6c8,pad)
            initial=c.read(c.data,0xfda0)
            for count in (1,5,6,8):
                def queue():
                    c.write(c.data,initial);put('timing_pad_count',count)
                    c.write(S+sy['timing_pad_pending'],pad*count)
                    put('timing_pad_pulses',0);put('timing_abort',0)
                queue();run('timing_scene_geometry');run('timing_pad_edges');run('timing_scene_geometry')
                want=c.read(c.data,0xfda0)
                queue();run('timing_edge_geometry')
                assert c.read(S+sy['timing_geometry_repeat'],2)==b'\0\1'
                run('timing_pad_edges');run('timing_scene_geometry');run('timing_geometry_history')
                assert c.read(c.data,0xfda0)==want
                counts['unchanged_queues']+=1
                # A transition in any byte of any queued position is guarded.
                for index in range(count*16):
                    queue();altered=bytearray(pad*count);altered[index]^=1
                    c.write(S+sy['timing_pad_pending'],bytes(altered))
                    run('timing_edge_geometry')
                    assert c.read(S+sy['timing_geometry_repeat'],2)==bytes(2)
                    counts['guarded_transitions']+=1
        # Occupancy holes, class 1/7/negative, camera slots, full and empty sets.
        # Destroy all backed-up slot fields, then require exact restoration.
        for slots in ([], [0], [0,1,7,10,60], list(range(61))):
            c.reset();c.write(c.data+0x96fe,bytes(128))
            for i,slot in enumerate(slots):c.data_value(0x96fe+2*slot,'h',(12,1,7,-1)[i%4])
            before=c.read(c.data,0xfda0)
            run('timing_scene_save_active')
            mask=c.read(S+sy['timing_scene_saved_mask'],64)
            expected=set(slots)|{61,62,63}
            assert {i for i,v in enumerate(mask) if v}==expected
            assert struct.unpack('>H',c.read(S+sy['timing_scene_saved_count'],2))[0]==len(expected)
            # Use the existing native-array contract, not the packed copy code.
            for at in range(sy['timing_scene_pose_ranges'],sy['timing_scene_snapshot_ranges'],4):
                relative,longs=struct.unpack('>hH',blob[at:at+4]);length=(longs+1)*4
                parts=3 if relative in (0x157a,0x245e) else 2 if relative==0x4078 else 1
                width=length//(64*parts)
                for slot in expected:
                    for part in range(parts):
                        dst=c.data+0x7ffe+relative+part*64*width+slot*width
                        c.write(dst,bytes([0xa5])*width)
            run('timing_scene_restore_active');assert c.read(c.data,0xfda0)==before
            counts['slot_roundtrips']+=1
        # Actual native allocator: first free at 10 or 60, exhausted pool,
        # option-off pass-through; lazy backup preserves registers and all data.
        for free in (10,60,None):
            for staged in (0,1):
                c.reset();c.write(c.data+0x96fe+20,struct.pack('>51h',*([7]*51)))
                if free is not None:c.data_value(0x96fe+free*2,'h',0)
                initial=c.read(c.data,0xfda0);ref.write(ref.data,initial)
                run('timing_scene_save_active');put('timing_scene_staged',staged)
                regs={r:0x1100+r for r in range(1,17) if r not in (5,8)}
                ref.run(0x2b632,registers=regs);c.run(0x2b632,registers=regs)
                assert c.read(c.data,0xfda0)==ref.read(ref.data,0xfda0)
                assert [c.reg(r) for r in range(1,18)]==[ref.reg(r) for r in range(1,18)]
                if staged:
                    run('timing_scene_end');assert c.read(c.data,0xfda0)==initial
                counts['allocator_pairs']+=1
        # Repeated saving of a reused staged slot must retain its first bytes.
        c.reset();c.write(c.data+0x96fe+20,bytes(102));c.data_value(0xa45c+20,'h',321);run('timing_scene_save_active')
        initial=c.read(c.data,0xfda0);put('timing_scene_staged',1)
        c.run(0x2b632);c.data_value(0xa45c+20,'h',1234);c.run(0x2b632)
        run('timing_scene_end');assert c.read(c.data,0xfda0)==initial
        # Negative control: bypass the lazy hook; the identical oracle fails.
        c.write(c.code+0x2b648,ref.read(ref.code+0x2b648,6))
        c.write(c.data,initial);run('timing_scene_save_active');put('timing_scene_staged',1)
        c.run(0x2b632);run('timing_scene_end')
        assert c.read(c.data,0xfda0)!=initial, 'missing lazy-save control accepted'
        c.close();ref.close()
    out.write_text(json.dumps(dict(counts=counts,models=[68020,68040],
        whole_data_equivalent=True,negative_controls=['missing range history','missing lazy allocation backup'],
        payload_sha256=hashlib.sha256(blob).hexdigest(),source_sha256=sources),indent=2)+'\n')
    print('PASS:',counts)


if __name__=='__main__':main()
