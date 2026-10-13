#!/usr/bin/env python3
"""Native clock ownership checks; varying pictures must not advance gameplay."""
import argparse,json,re,struct
from pathlib import Path
from timing_audit_check import CPU
from cd32_runtime import ROOT,locate
S=0x180000

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('build',type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args()
    out=a.output.resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():raise ValueError('new tmp output required')
    memory=(ROOT/'tmp/phase7-combat-controls/start-fast.bin').read_bytes();layout=locate(memory)
    blob=(a.build/'payload.bin').read_bytes();sym={n:int(o,16) for o,n in re.findall(r'^([0-9A-F]{8}) (\S+)$',(a.build/'slave.lst').read_text(),re.M)}
    rows=[]
    for model in (2,4):
        for pictures in (0,1,5,9):
            c=CPU(memory,layout,model);c.write(S,blob)
            def setv(n,f,v):c.write(S+sym[n],struct.pack('>'+f,v))
            def run(n,args=b'',end=None):c.run(S+sym[n]-c.code,args,end=end)
            setv('timing_game','I',c.code);setv('timing_active','H',1);setv('timing_in_world','H',1)
            c.write(c.data+0xa970,bytes([4])*9) # no damaged subsystem opportunities in visual isolation
            c.data_value(0x6f18,'I',0x12345678);c.data_value(0xa956,'h',100)
            c.data_value(0xadc,'h',1);c.data_value(0x8c,'h',100)
            for tick in range(20):
                c.data_value(0x914c,'H',tick)
                run('timing_emission_clock');assert c.reg(9)&0xffff==tick&3
                run('timing_presentation_tick')
                for picture in range(pictures):
                    c.data_value(0x9150,'H',picture)
                    run('timing_emission_clock');assert c.reg(9)&0xffff==tick&3
                    run('timing_message_draw');run('timing_sim_draw')
                    run('timing_portrait_random',struct.pack('>hh',0,7));assert 0<=c.reg(9)&0xffff<=7
                    run('timing_portrait_clock');assert bool(c.reg(17)&4)==(tick%2==0)
            assert c.data_value(0xa956,'h')==80
            assert c.data_value(0x8c,'h')==80
            assert c.data_value(0x6f18,'I')==0x12345678
            visual=c.read(S+sym['timing_visual_seed'],4).hex()
            for delta,initial in ((0,20),(1,20),(4,20),(20,20),(21,20)):
                setv('timing_selection_delta','H',delta);c.data_value(0xb2aa,'h',initial)
                run('timing_selection',end=0x4c56 if initial>delta else 0x4b1e)
                assert c.data_value(0xb2aa,'h')==initial-delta
            setv('timing_active','H',0);setv('timing_in_world','H',0)
            c.data_value(0x9150,'H',7);run('timing_emission_clock');assert c.reg(9)&0xffff==3
            run('timing_message_draw');run('timing_sim_draw')
            assert c.data_value(0xa956,'h')==79 and c.data_value(0x8c,'h')==79
            run('timing_portrait_random',struct.pack('>hh',0,7));assert c.data_value(0x6f18,'I')!=0x12345678
            rows.append(dict(model=model,pictures_per_tick=pictures,visual_seed=visual));c.close()
    # Whole native damaged-system polling: ten world calls, any number of
    # HUD calls. Compare its RNG and subsystem results against ten originals.
    for model in (2,4):
        reference=None
        for pictures in (0,1,5):
            c=CPU(memory,layout,model);c.write(S,blob)
            c.write(S+sym['timing_game'],struct.pack('>I',c.code))
            c.write(S+sym['timing_active'],struct.pack('>H',1))
            c.write(c.data+0xa970,bytes([3])*9)
            c.data_value(0x6f18,'I',0x12345678)
            c.data_value(0xa956,'h',0);c.data_value(0xadc,'h',0)
            for _ in range(10):
                c.run(S+sym['timing_presentation_tick']-c.code)
                for _ in range(pictures):c.run(S+sym['timing_systems_draw']-c.code)
            state=(c.read(c.data+0x6f18,4),c.read(c.data+0xa970,9))
            if reference is None:reference=state
            else:assert state==reference
            assert state[0]!=struct.pack('>I',0x12345678)
            c.close()
    assert len({r['visual_seed'] for r in rows})==1
    out.mkdir(parents=True);(out/'report.json').write_text(json.dumps(dict(cases=rows,game_rng_preserved=True,native_modal_paths=True),indent=2)+'\n')
    print('PASS: native timers, emission, visual RNG and original modal paths across four draw schedules')
if __name__=='__main__':main()
