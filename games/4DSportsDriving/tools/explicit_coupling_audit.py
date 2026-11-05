#!/usr/bin/env python3
"""Audit causal two-stage candidate against unchanged original handling limits."""
import hashlib,json,re,struct
from pathlib import Path
from simulation_fixture import read_fixture,compare
root=Path('tmp/prof');candidate=root/'explicit-coupling-candidate';control=root/'explicit-coupling-identity'
cd=json.loads((control/'explicit-result.json').read_text());nd=json.loads((candidate/'explicit-result.json').read_text())
assert cd['identity'] and not nd['identity']
initial=compare(read_fixture(control),read_fixture(candidate));assert not initial['mismatches']
ref={v['tick']:v for v in json.loads((root/'natural-crest20/bridge.json').read_text())['rows']}
canonical={v['tick']:v for v in json.loads((root/'crest-d9e7903/bridge.json').read_text())['rows']}
criteria_file=root/'natural-crest-criteria.json';criteria=json.loads(criteria_file.read_text());sha=hashlib.sha256(criteria_file.read_bytes()).hexdigest();assert sha=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
results=[]
for p,d in ((control,cd),(candidate,nd)):
 text=(p/'explicit-log.txt').read_text();raw=[list(map(int,v.split())) for v in re.findall(r'^BODY (.*)$',text,re.M)]
 assert [v[0] for v in raw]==list(range(451,681))
 assert len(re.findall(r'^APPLIED ',text,re.M))==230
 bodies={v[0]:dict(zip(('x','y','z','heading','pitch','roll'),v[1:7])) for v in raw}
 aligned=0
 for tick,hz,state in read_fixture(p,'explicit-end.bin'):
  if tick in bodies:
   b=bodies[tick];assert tuple(b[k] for k in ('x','y','z'))==struct.unpack_from('>iii',state,0x152)
   assert tuple(b[k] for k in ('heading','pitch','roll'))==struct.unpack_from('>hhh',state,0x16a);aligned+=1
 if d['identity']:
  assert d['matching_full_states']==64
  assert all(all(v[k]==canonical[t][k] for k in v) for t,v in bodies.items())
 errors={k:bodies[650][k]-ref[260][k] for k in ('y','z','pitch')}
 common={k:max(abs(v[k]-ref[t*2//5][k]) for t,v in bodies.items() if t%10==0) for k in errors}
 results.append(dict(identity=d['identity'],verified=d['verified'],verified_writes=d['verified_writes'],aligned_states=aligned,
  errors_at_13s=errors,max_common_errors_in_window=common,nonzero_corrections=sum(any(r['correction']) for r in d['records']),
  final_residue=d['records'][-1]['residue'],trace_sha256=hashlib.sha256((p/'explicit-result.json').read_bytes()).hexdigest()))
passed=all(results[1]['max_common_errors_in_window'][k]<=criteria['envelope'][k] for k in ('y','z','pitch'))
report=dict(accepted=False,window_passes_y_z_pitch=passed,criteria_sha256=sha,limits={k:criteria['envelope'][k] for k in ('y','z','pitch')},runs=results,
 scope='Window451..680 only; a failure rejects this candidate, passing cannot establish full16s handling, general tracks/rotation, replay or capacity.')
(root/'explicit-coupling-audit.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
