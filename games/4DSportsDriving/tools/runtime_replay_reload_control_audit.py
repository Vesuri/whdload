#!/usr/bin/env python3
"""Compare same-graphics reload with the prior FULL/FAST replay evidence."""
import json,hashlib,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1];p=root/'tmp/runtime-reload-full-control';old=root/'tmp/runtime-render-replay'
sha=lambda b:hashlib.sha256(b).hexdigest()
f=(p/'first/states.bin').read_bytes();s=(p/'second/states.bin').read_bytes()
assert len(f)==len(s)==250*1510
assert f==(old/'full/states.bin').read_bytes()
assert s==(old/'fast/states.bin').read_bytes()
for label in ('first','second'):
 c=json.loads((p/label/'capture.json').read_text());assert c['detail']==0 and c['states']==250
 assert [r['tick'] for r in c['rows']]==list(range(1351,1601))
 end=json.loads((p/(label+'-end.json')).read_text());assert end['perf_failure']==end['sim_schedule_overflow']==0
m=json.loads((p/'start/anchor.json').read_text());a=m['data_base']+0x7ffe-m['memory_base']
bs=[(p/(n+'.bin')).read_bytes() for n in ('loaded-first','loaded-second')]
paths=[]
for b in bs:
 off=struct.unpack_from('>I',b,a-0x17a4)[0]-m['memory_base'];paths.append(b[off:off+1802])
groups={'player':(338,546),'opponent':(546,754),'rng':(1120,1126),'time':(1278,1310),'auxiliary':(1310,1502),'camera':(1502,1510),'complete':(0,1510)}
equal={name:sum(f[i*1510+lo:i*1510+hi]==s[i*1510+lo:i*1510+hi] for i in range(250)) for name,(lo,hi) in groups.items()}
r={'checkpoint_cursors':[1351,1600],'checkpoints':250,'first_matches_prior_full':True,'second_matches_prior_fast':True,'equal_first_second':equal,'path_changed_bytes':sum(x!=y for x,y in zip(*paths)),'first_states_sha256':sha(f),'second_states_sha256':sha(s),'scope':'Same process, same replay, FULL graphics both runs. Native keyboard load and ordinary runtime; no guest memory writes. Reload reproduces the previous opponent divergence without a graphics change.','unconfirmed_hypothesis':'Original 1642A appears to use sped resource for track-piece costs although path is separately loaded; needs live pointer/read validation. Attempted resource breakpoint during monitor-profile UI navigation produced no dump, so supplies no evidence.'}
(p/'validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
