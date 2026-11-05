#!/usr/bin/env python3
"""Check ordinary-runtime native normal/double replay evidence."""
import pathlib,json,hashlib,struct
r=pathlib.Path('tmp/replay-speeds-runtime-67');m=json.loads((r/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
def semantic(b):
    parts=[b[a-0xa80:a-0x620],b[a+0x228:a+0x22e]]
    for k,n in [(b'4DA4PHYS',152),(b'4DTSTATE',32),(b'4DAUXPHY',192),(b'4DCAM050',8)]:
        p=b.index(k)+12;assert struct.unpack_from('>H',b,p-2)[0]==n;parts.append(b[p:p+n])
    out=b''.join(parts);assert len(out)==1510;return out
report={'windows':{},'equal_states':[],'scope':'Ordinary runtime, native keyboard replay controls, FULL solo C2=1, private 040/PAL emulator WARP1. No guest memory writes. Normal window then native double-speed transition. No half-speed UI, disk replay, hardware capacity or handling claim.'}
for label,speed,published in [('normal',0,250),('double',3,500)]:
    d=json.loads((r/(label+'-window.json')).read_text());x,y=d['start'],d['end'];ticks=[z[1] for z in d['bodies']]
    assert y['sim_clock_fields']-x['sim_clock_fields']==250
    assert y['sim_schedule_ticks']-x['sim_schedule_ticks']==published
    assert ticks==list(range(x['consumer']+1,y['consumer']+1))
    for st in (x,y):
        assert st['replay_speed']==speed and st['mode']==2 and st['replay_pause']==0
        assert st['active_rate']==st['recorded_rate']==50
        assert st['perf_failure']==st['sim_schedule_overflow']==0
    report['windows'][label]={'fields':250,'published':published,'completed':len(ticks),'start_consumer':x['consumer'],'end_consumer':y['consumer'],'initial_imported_debt':x['imported']-x['consumer'],'final_imported_debt':y['imported']-y['consumer']}
for label,t in [('normal',200),('double',400),('double',600)]:
    live=semantic((r/f'live-{t}.bin').read_bytes());play=semantic((r/f'{label}-{t}.bin').read_bytes());assert live==play,(label,t)
    report['equal_states'].append({'speed':label,'tick':t,'bytes':len(live),'sha256':hashlib.sha256(live).hexdigest()})
report['runtime_sha256']=hashlib.sha256((r/'start/slave.slave').read_bytes()).hexdigest()
(r/'window-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
