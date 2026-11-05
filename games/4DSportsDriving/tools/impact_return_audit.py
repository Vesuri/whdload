#!/usr/bin/env python3
"""Screen first-contact/sustained-return hypothesis with frozen coupled-course gates."""
import json,hashlib,collections,sys
from pathlib import Path
mode=sys.argv[1] if len(sys.argv)>1 else 'impact-return';assert mode in ('native-geometric-pitch','crossing-precision','impact-return','anchored-support','air-zero','acquired-boundary','tangent-support','unilateral-tangent','fine-residual-push','fine-existing-push','rate-push-bias','orthogonal-travel','coherent-shallow','shallow-alignment','extension-rate-cap','exponential-extension','negative-extension-rate','negative-extension-stored','explicit-contact-order','normal-clearance-response')
r=Path('tmp/prof');cp=r/'natural-crest-criteria.json';fp=r/'native-contact-phase-criteria.json';c=json.loads(cp.read_text());f=json.loads(fp.read_text())
assert hashlib.sha256(cp.read_bytes()).hexdigest()=='90570d37e39d7fbdf804bbc497959ffe30e60f51bbb60c3e938f041c1d3401db'
assert hashlib.sha256(fp.read_bytes()).hexdigest()=='74afe3d039870269ccf4d160434ec52f05fe195dfb8dc6c338a3aeca613d64ce'
reports=[]
for phase in ('nominal','minus64','plus64'):
 suffix='' if phase=='nominal' else '-'+phase;p=r/('coupled-course-'+mode+suffix+'.json');rows=json.loads(p.read_text())['rows'];assert [v['tick']for v in rows]==list(range(6,801));ix={v['tick']:v for v in rows}
 native={v['tick']:v for v in json.loads((r/('natural-crest20' if phase=='nominal' else 'phase-'+phase+'-native20')/'bridge.json').read_text())['rows']}
 maxima={k:max(abs(v[k]-native[v['tick']*2//5][k]) for v in rows if v['tick']>=450 and v['tick']%10==0) for k in ('x','y','z','pitch','speed')}
 bands=[]
 for t,fields in f['common_bands'].items():
  tick=int(t)*5
  if tick not in ix:continue
  for k in ('x','y','z','pitch'):
   band=fields[k];value=ix[tick][k]
   if not band['low']<=value<=band['high']:bands.append(dict(tick=tick,field=k,value=value,**band))
 gates={}
 if phase=='nominal':
  metrics={'final_'+k:rows[-1][k] for k in ('x','y','z','pitch','speed')};metrics.update(peak_height=max(v['y'] for v in rows),minimum_pitch=min(v['pitch'] for v in rows),maximum_pitch=max(v['pitch'] for v in rows))
  for k,value in metrics.items():
   if k in c['limits']:gates[k]=dict(value=value,reference=c['native20']['metrics'][k],limit=c['limits'][k],passed=abs(value-c['native20']['metrics'][k])<=c['limits'][k])
  for k,value in maxima.items():gates['common_'+k]=dict(value=value,limit=c['envelope'][k],passed=value<=c['envelope'][k])
 baseline=json.loads((r/('coupled-course-baseline'+suffix+'.json')).read_text())['rows']
 baseline_maxima={k:max(abs(v[k]-native[v['tick']*2//5][k]) for v in baseline if v['tick']>=450 and v['tick']%10==0) for k in ('x','y','z','pitch','speed')}
 worst_ticks={k:max((v for v in rows if v['tick']>=450 and v['tick']%10==0),key=lambda v:abs(v[k]-native[v['tick']*2//5][k]))['tick']for k in ('y','pitch')}
 reports.append(dict(phase=phase,maxima=maxima,baseline_maxima=baseline_maxima,worst_ticks=worst_ticks,original_gates=gates,original_failures=[k for k,v in gates.items() if not v['passed']],phase_band_failures=bands,phase_band_failure_counts=dict(collections.Counter(v['field']for v in bands))))
hypothesis=('Unscaled geometric128 return on support acquisition; exact2/5 return cap on consecutive supported50Hz steps. Fresh separation resets support history. Native modes unchanged.' if mode=='impact-return' else 'Existing acquired-depth support constraint, now with full engine feedback from the start of the course.')
if mode=='air-zero':hypothesis='Continue nonzero falling velocity through coarse zero only while raw normal depth stays positive; resting behavior and gravity law unchanged.'
if mode=='acquired-boundary':hypothesis='Acquired native contact depth is the same geometric boundary for gravity activation, support, suspension and airborne recontact on that face.'
if mode=='tangent-support':hypothesis='Acquired-face support advances each wheel by surface tangent distance with fractional rotation carries; native impact and face change preserved.'
if mode=='unilateral-tangent':hypothesis='Tangent support only while proposed endpoint penetrates acquired depth; separation falls back to native response.'
if mode=='fine-residual-push':hypothesis='Only full-tangent/crossing residual push uses raw normal plane depth; native branch/gravity/suspension unchanged.'
if mode=='fine-existing-push':hypothesis='Use raw depth magnitude only where native residual is negative; retain native push/no-push decision.'
if mode=='rate-push-bias':hypothesis='Analytic correction plus2/5 of native-minus-analytic rounding bias, exact per-axis carries, native push activation.'
if mode=='orthogonal-travel':hypothesis='Orthogonalize and normalize contact tangent against the selected collision normal; other response laws unchanged.'
if mode=='coherent-shallow':hypothesis='Common centroid correction for uncompressed resting wheels on one face with q=-1/0; all other contact laws preserved.'
if mode=='shallow-alignment':hypothesis='Limit overshoot across plane-normal pitch during identical-face shallow resting alignment; native wheel/suspension/centroid retained.'
if mode=='extension-rate-cap':hypothesis='Positive suspension extension closes geometric gap up to an exact2/5 native192 movement cap; no unused capacity banking.'
if mode=='exponential-extension':hypothesis='Native20-derived exponential unsaturated extension gain, unchanged saturated speed, high precision model-only carries.'
if mode=='negative-extension-rate':hypothesis='Scale native negative-clearance extension delta by2/5 with fifth carries; preserve native body correction formula and all other branches.'
if mode=='negative-extension-stored':hypothesis='Scale only persistent negative-branch extension delta by2/5; preserve native same-step returned body correction.'
if mode=='explicit-contact-order':hypothesis='Explicit discarded body predictor determines3/4 movement-order correction; requery/contact once from the same initial state and commit only the final result.'
if mode=='normal-clearance-response':hypothesis='Response-local Y and branch selection use the penetration query normal; preserve native matrix-local X/Z and other response geometry.'
if mode=='crossing-precision':hypothesis='Refine matrix-local crossing distance using raw world coordinates; retain native branch, gravity, suspension, span denominator, tangent and coarse residual push.'
if mode=='native-geometric-pitch':hypothesis='Original absolute endpoint-axis pitch lookup and native deadband at50Hz; wheel forces, response, suspension, centroid and engine unchanged.'
out=dict(hypothesis=hypothesis,cases=reports,decision='rejected' if any(v['original_failures']or v['phase_band_failures']for v in reports)else'needs further validation',criteria_sha256=hashlib.sha256(cp.read_bytes()).hexdigest(),phase_criteria_sha256=hashlib.sha256(fp.read_bytes()).hexdigest(),scope='795 recurrent coupled steps in each phase; baseline nominal reconfirmed exact. Offline straight stock car only, not runtime, preload/drop, full-contact domain or acceptance proof.')
(r/(mode+'-audit.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({**out,'cases':[{k:v for k,v in q.items()if k not in ('phase_band_failures','original_gates')}for q in reports]},indent=2))
