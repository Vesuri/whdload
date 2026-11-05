#!/usr/bin/env python3
"""Verify natural continuation before attributing a position-only intervention."""
import json,hashlib,sys
from pathlib import Path
from simulation_fixture import read_fixture,compare
P=Path('tmp/prof');control=P/'approach550-control';reference=json.loads((P/'crest-d9e7903/bridge.json').read_text());ref={r['tick']:r for r in reference['rows']};data=json.loads((control/'bridge.json').read_text());rows=data['rows'];assert [r['tick'] for r in rows]==list(range(1,101))
def initial(name):
 cap=P/name;sample=read_fixture(cap)[0];assert sample[:2]==(0,50)
 s=sample[2];seed=s[0x152:0x222]+s[0x466:0x466+152]+s[0x460:0x466]
 expected=(Path('tmp/fixtures')/name/'seed.bin').read_bytes();assert seed==expected
 return hashlib.sha256(seed).hexdigest()
def differences(actual,expected):return {k:[v,expected[k]] for k,v in actual.items() if k!='tick' and v!=expected[k]}
errors=[dict(tick=r['tick'],original_tick=r['tick']+550,differences=differences(r,ref[r['tick']+550])) for r in rows];errors=[r for r in errors if r['differences']]
report=dict(control_seed_sha256=initial('approach550-control'),control_updates=100,natural_matching_updates=100-len(errors),control_differences=errors,required_continuation_ticks=100,continuation_exact=not any(r['tick']<=100 for r in errors))
(P/'approach550-control/continuation-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));assert report['continuation_exact'],'Fresh race context does not reproduce the original first flight'
if '--candidate' in sys.argv:
 cap=P/'approach550-native-position';candidate=json.loads((cap/'bridge.json').read_text())['rows'];assert [r['tick'] for r in candidate]==list(range(1,101));report['candidate_seed_sha256']=initial('approach550-native-position')
 native={r['tick']:r for r in json.loads((P/'natural-crest20/bridge.json').read_text())['rows']};lookup={r['tick']:r for r in candidate};base={r['tick']:r for r in rows};report['common_time']=[]
 for tick in range(10,101,10):
  t=(550+tick)/50;n=native[(550+tick)*2//5];b=base[tick];c=lookup[tick]
  report['common_time'].append(dict(time=t,control_error={k:b[k]-n[k] for k in ('y','z','pitch')},candidate_error={k:c[k]-n[k] for k in ('y','z','pitch')},intervention_delta={k:c[k]-b[k] for k in ('y','z','pitch')}))
 report['scope']='Exact 100-update continuation required. Only integer body XYZ position changed to native20 values at11.0 seconds; private fractions, velocity, orientation, suspension and RNG retained. This is a causal diagnostic for the recorded entry state, not a runtime correction or full handling acceptance.'
 (P/'approach550-position-split.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['common_time'],indent=2))
