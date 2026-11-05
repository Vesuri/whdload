#!/usr/bin/env python3
"""Read-only trace of native pitch reconstruction during a seeded ramp fall."""
import json,math,re,struct,sys
from pathlib import Path
from profile_window import command,ROOT
cap=Path(sys.argv[1]).resolve();meta=json.loads((cap/'anchor.json').read_text())
assert meta['opponent']==0
rate=meta['active_simulation_word'];steps=rate*4//5-meta['simulation_tick'];assert steps>0;g=meta['game_base'];aa=meta['data_base']+0x7ffe
script=f'''gdb delete
set $n=0
break *{g+0xd55a:#x}
commands
silent
printf "INPUT %u %d %d %d %u\\n", *(unsigned short *)($a4-0x940), *(short *)($a4-0x914), *(short *)$sp, *(short *)($sp+2), *(unsigned char *)($a4-0x86d)
continue
end
break *{g+0xd55e:#x}
commands
silent
printf "ANGLE %u %d\\n", *(unsigned short *)($a4-0x940), (short)$d0
continue
end
break *{g+0xd584:#x}
commands
silent
printf "FINAL %u %d\\n", *(unsigned short *)($a4-0x940), *(short *)($a4+0xbaa)
continue
end
break *{g+0xe7b4:#x}
commands
silent
set $n=$n+1
printf "STEP %u %d %d\\n", *(unsigned short *)($a4-0x940), *(int *)($a4-0x92a), *(short *)($a4-0x914)
if $n<{steps}
continue
end
end
continue
info registers pc
'''
(cap/'pitch-probe.gdb').write_text(script);out=command(script);(cap/'pitch-probe.txt').write_text(out)
assert int(re.search(r'^pc\s+0x([0-9a-f]+)',out,re.M)[1],16)==g+0xe7b4
records={tag:[list(map(int,s.split())) for s in re.findall(r'^'+tag+r' (.*)$',out,re.M)] for tag in ('INPUT','ANGLE','FINAL','STEP')}
assert len(records['STEP'])==steps
raw=(ROOT/'tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes();base=0x3a1dc+0x7ffe;table=raw[base-0x386c:base-0x386c+257]
def native(x,y):
    octant=(4 if x<0 else 0)+(2 if y<0 else 0);x,y=abs(x),abs(y)
    if x==y:
        if not x:return 0
        angle=128
    else:
        if x>y:x,y=y,x;octant+=1
        quotient=(x<<16)//y;angle=table[(quotient>>8)+((quotient>>7)&1)]
    return (angle,256-angle,512-angle,256+angle,-angle,angle-256,angle-512,-256-angle)[octant]
def wrap(v):return (v+512)%1024-512
angles=dict(records['ANGLE']);final=dict(records['FINAL']);rows=[]
for tick,old,x,y,contact in records['INPUT']:
    assert angles[tick]==native(x,y),(tick,x,y,angles[tick],native(x,y))
    quantized=angles[tick]-256
    assert final[tick]==(0 if abs(quantized)<2 else quantized)
    exact=wrap(math.atan2(x,y)*512/math.pi-256)
    rows.append(dict(tick=tick,old_pitch=old,x=x,y=y,contact=contact,exact_pitch=exact,quantized_pitch=quantized,final_pitch=final[tick],discarded=wrap(exact-final[tick])))
result=dict(rate=rate,updates=steps,lookup_calls=len(rows),rows=rows,steps=records['STEP'],
            deadzone_clears=sum(r['quantized_pitch']!=0 and r['final_pitch']==0 for r in rows),
            discarded_sum=sum(r['discarded'] for r in rows),
            scope='Exact native atan and deadzone reproduction; summed losses diagnose this observed closed-loop path and do not predict a corrected trajectory.')
(cap/'pitch-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ('rows','steps')},indent=2))
command(f'gdb delete\ndump binary memory {cap.relative_to(ROOT)}/pitch-end.bin 0x200000 0x600000')
