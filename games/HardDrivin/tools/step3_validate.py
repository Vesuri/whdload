import json,subprocess,struct,hashlib
from pathlib import Path
from check_disabled import check
P=Path(__file__).resolve().parents[1]/'tmp/prof';B=P.parent/'build';r={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r['unchanged_builds']={k:sha(B/('s3-'+k+'.slave'))==sha(B/('s2-final-'+k+'.slave')) for k in ['normal','drive','attract']};assert all(r['unchanged_builds'].values())
r['normal_sha256']=sha(B/'s3-normal.slave')
r['controlled']={}
for n in ['a500','a500-slow','020','040']:
 p=P/('s3-stepinput-'+n);m=json.loads((p/'metadata.json').read_text());sz=m['snapshot_size'];b=subprocess.check_output(['zstd','-qdc',str(p/'physics.bin.zst')]);bs=[b[i:i+sz] for i in range(0,len(b),sz)];assert len(bs)==108
 assert all(struct.unpack_from('>HH',b,0x95fa-0x8002)==(320,200) for b in bs)
 v=check(p,['VERIFY_DRIVE','VERIFY_STEPINPUT']+(['VERIFY_SLOW'] if n=='a500-slow' else []));assert v['passed'];(p/'range-check.json').write_text(json.dumps(v,indent=2)+'\n')
 speed=[struct.unpack_from('>h',b,0x992c-0x8002)[0] for b in bs]
 r['controlled'][n]=dict(steps=len(bs),last_field=m['events'][-1]['field'],speed60_step=next((i for i,x in enumerate(speed) if x>=60),None),speed100_step=next((i for i,x in enumerate(speed) if x>=100),None),crash_steps=sum(b[0x9606-0x8002]!=0 for b in bs),ranges_pass=True,inputs_pass=True)
comp=json.loads((P/'step3-comparison.json').read_text());assert all(v['car']['first_difference'] is None and v['car']['compared']==108 for v in comp['s3-stepinput-'].values());r['controlled_car_equivalence']=True
impact=json.loads((P/'s3-profile-a500-impact/window-metrics.json').read_text());assert impact['fields']==500 and impact['independent_counter_validated'];r['impact_independent_field_match']=True
r['impact_collision']=[x for x in json.loads((P/'step3-costs.json').read_text())['impact']['rows'] if x['class']=='collision']
# Full native A/B pass spacings, retain replay gaps as separate phases.
p=P/'drive-a500-jump1/capture.log';import re
events=[(int(o,16),int(f)) for o,f in re.findall(r'^EVENT ([0-9a-f]+) (\d+)$',p.read_text(),re.M)]
for name,lo,hi in [('A',1,1251),('B',3000,5600)]:
 fs=[f for o,f in events if o==0xb4 and lo<=f<hi];gaps=[b-a for a,b in zip(fs,fs[1:])];r['swap_gaps_'+name]=dict(min=min(gaps),max=max(gaps))
(P/'step3-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
