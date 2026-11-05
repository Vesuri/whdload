from pathlib import Path
import json,hashlib,subprocess,sys
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def evidence(p):return dict(path=str(p.relative_to(r)),sha256=sha(p))
b=r/'tmp/build/render-h2/FerrariFormulaOne.slave';control=r/'tmp/build/render-h2-control/FerrariFormulaOne.slave'
assert b.read_bytes()==(r/'tmp/build/render-h2-rebuild/FerrariFormulaOne.slave').read_bytes()
assert len(b.read_bytes())==len(control.read_bytes()) and sum(x!=y for x,y in zip(b.read_bytes(),control.read_bytes()))==1
report=dict(status='accepted-by-user-on-completed-evidence',scope='SPS 0481 PAL H2 fine rendering, equal-layout A/B; human full races and physical hardware deferred',candidate=evidence(b),control=evidence(control),rebuild_exact=True,evidence=[],frames={},controls={},legacy={})
for name in ['scratch','matched-profile','dma','traces','performance']:
 p=r/f'manifest/render-h2-{name}.json';j=read(p)
 if name!='performance' and 'status' in j:assert j['status']=='passed',(name,j['status'])
 report['evidence'].append(evidence(p))
p=r/'tmp/step5/c4-q03-render-profile-a1200-fast-h2-candidate/audit.json';assert read(p)['status']=='passed';report['evidence'].append(evidence(p))
assert all(x['status']=='passed' for x in read(r/'manifest/render-h2-dma.json').values())
for scene in ['normal','grid','dense']:
 paths=[r/f'tmp/step5/c4-q03-h2-frame-production-a1200-fast-h2-{scene}-{arm}' for arm in ['control','candidate']]
 js=[read(p/'result.json') for p in paths];assert js[0]['frames']==js[1]['frames'] and len(js[0]['frames'])==30
 report['frames'][scene]=dict(count=30,results=[evidence(p/'result.json') for p in paths])
a,c=[r/f'tmp/step5/c4-q03-drive-state-production-a1200-fast-h2-state-{arm}' for arm in ['control','candidate']]
assert (a/'records.bin').read_bytes()==(c/'records.bin').read_bytes()
assert read(a/'private.json')==read(c/'private.json')
assert read(a/'result.json')['steps']==read(c/'result.json')['steps']==100
report['state']=dict(updates=100,semantic_blocks=27,records=[evidence(p/'records.bin') for p in [a,c]],private=[evidence(p/'private.json') for p in [a,c]])
report['elapsed']=[]
for arm in ['control','candidate']:
 p=r/f'tmp/step5/c4-q03-drive-timing-a1200-fast-h2-normal-{arm}/result.json';j=read(p);assert j['status']=='passed' and j['error']==0 and abs(j['error_percent'])<=.25
 report['elapsed'].append(dict(arm=arm,result=evidence(p),seconds=j['elapsed_seconds'],error_percent=j['error_percent']))
report['deferred']=['060 grid candidate and dense pair', 'fresh H2 native input/manual-gear and 040/MMU/32MB control checks', 'H2 pause/tow/pit/menu/re-entry, ledger restoration and signature-failure injection', 'fresh four-profile CUSTOM2=0 and CUSTOM1 option comparisons']
report['decision']='User: The numbers are good. Accept this, let us move on. Remaining orchestration stopped; no full H2 release qualification claimed.'
report['harness']=[evidence(p) for p in sorted((r/'tools').glob('*h2*.py'))]
(r/'manifest/render-h2-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('Completed H2 evidence verified; user acceptance and deferred gates recorded')
