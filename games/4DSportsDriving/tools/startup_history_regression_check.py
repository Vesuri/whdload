#!/usr/bin/env python3
"""Verify current-source native preservation, self-tests and replay seek evidence."""
import pathlib,json,re,struct,hashlib
from simulation_fixture import read_fixture,compare
r=pathlib.Path('tmp/startup-history-regression');p=r/'seek50-direct';m=json.loads((p/'anchor.json').read_text());s={k:int(v,16)for k,v in re.findall(r'^(\w+)\s+00:([0-9A-Fa-f]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};b=(p/'memory.bin').read_bytes();base=m['marker']+8-s['tape_game']-m['memory_base']
counts={n:struct.unpack_from('>I',b,base+s[n])[0]for n in s if n.endswith('_passed')}
for n,v in dict(sim_physics_passed=4342,sim_history_passed=40,sim_schedule_replay_passed=19,sim_schedule_reset_passed=2,sim_schedule_modal_passed=4).items():assert counts[n]==v,(n,counts[n])
assert struct.unpack_from('>I',b,base+s['perf_failure'])[0]==0
seek=json.loads((p/'replay-check.json').read_text());assert seek['restored_tick']==150 and seek['replayed_tick']==155 and seek['replay_equal']
native={}
for hz in (10,20):
 cap=r/('native'+str(hz));result=compare(read_fixture(cap),read_fixture(r/('baseline'+str(hz))))
 assert result['samples']==result['equal_samples'] and result['samples']>=21,result
 assert all(len(state)==1510 for _,_,state in read_fixture(cap))
 native[str(hz)]=result
report=dict(verification_sha256=hashlib.sha256((p/'slave.slave').read_bytes()).hexdigest(),startup_selftests=counts,seek=seek,native_comparisons=native,bytes_per_native_sample=1510,excluded_attempts=['seek50: runtime040/GAME settings missed requested checkpoint; explicitly interrupted and closed; not evidence','Historical display-wait native references had different initial states and sample endpoints; use controlled current/parent scheduler source pairs instead'],scope='Current source 1e253c0. VERIFY fixture; native20/10 equal-state preservation, A4000 checkpoint restoration and deterministic seek. Separate ordinary-runtime startup/end proof in startup-history-fix. Not broader handling or hardware acceptance.')
(r/'validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
