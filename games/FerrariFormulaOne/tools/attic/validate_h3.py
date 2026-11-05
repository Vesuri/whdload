from pathlib import Path
import json,hashlib,sys
from PIL import Image
r=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def evidence(p):return dict(path=str(p.relative_to(r)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
report=dict(status='passed',scope='H3 SPS0481 PAL fine-path rendering; physical hardware and human full races deferred',evidence=[],frames={},controls={},legacy={})
for n in ['build-audit','source-audit','matched-profile','performance']:
 p=r/f'manifest/render-h3-{n}.json';j=read(p);assert j['status']=='passed',(n,j['status']);report['evidence'].append(evidence(p))
road=[read(r/f'tmp/step5/c4-q03-render-profile-a1200-fast-h3-matched-{a}/road-analysis.json') for a in ['control','candidate']]
def compact(j):
 seq=[]
 for f in j['display_fields'][1:-1]:
  h=f['pixel_dma_sha256']
  if not seq or seq[-1]!=h:seq.append(h)
 return seq
assert compact(road[0])==compact(road[1]) and len(compact(road[0]))==15
assert all(t['safe'] for t in road[1]['transitions']) and len(road[1]['display_banks'])==2
palette=read(r/'manifest/render-h3-palette.json');assert palette['native_colour00_sequence_exact'] and palette['copper_palette_writes_exact_including_beam_slots']
report['intermediate_palette_scope']=palette['note'];report['preexisting_cleanup']='Remove unconditional B8 COLOR00 diagnostic pulse separately; it is absent from the original game.'
for n in ['dma','traces','palette','field-rgb']:
 p=r/f'manifest/render-h3-{n}.json';j=read(p)
 if n=='dma':assert all(x['status']=='passed' for x in j.values())
 report['evidence'].append(evidence(p))
p=r/'tmp/step5/c4-q03-render-profile-a1200-fast-h3-candidate/audit.json';assert read(p)['status']=='passed';report['evidence'].append(evidence(p))
for scene in ['normal','grid','dense']:
 paths=[r/f'tmp/step5/c4-q03-h3-frame-production-a1200-fast-h3-{scene}-{arm}' for arm in ['control','candidate']];a,b=[read(p/'result.json') for p in paths];assert a['frames']==b['frames'] and len(a['frames'])==30
 for directory in paths:
  for row in read(directory/'result.json')['frames']:
   image=Image.open(directory/f"frame-{row['update']}.png").convert('RGB');assert list(image.size)==row['size'] and hashlib.sha256(image.tobytes()).hexdigest()==row['pixel_sha256']
 report['frames'][scene]=dict(count=30,results=[evidence(p/'result.json') for p in paths])
a,b=[r/f'tmp/step5/c4-q03-drive-state-production-a1200-fast-h3-state-{arm}' for arm in ['control','candidate']]
assert (a/'records.bin').read_bytes()==(b/'records.bin').read_bytes() and read(a/'private.json')==read(b/'private.json')
assert read(a/'result.json')['steps']==read(b/'result.json')['steps']==100
report['state']=dict(updates=100,semantic_blocks=27,records=[evidence(p/'records.bin') for p in [a,b]],private=[evidence(p/'private.json') for p in [a,b]])
report['elapsed']=[]
for arm in ['control','candidate']:
 p=r/f'tmp/step5/c4-q03-drive-timing-a1200-fast-h3-normal-{arm}/result.json';j=read(p);assert j['status']=='passed' and j['error']==0 and j['error_percent']<=.25
 report['elapsed'].append(dict(arm=arm,seconds=j['elapsed_seconds'],error_percent=j['error_percent'],result=evidence(p)))
for option in ['0','1']:
 p=r/f'manifest/render-h3-default-c{option}-validation.json';j=read(p);assert j['status']=='passed' and all(v['passed'] for v in j['profiles'].values()) and len(j['profiles'])==4;report['legacy'][option]=evidence(p)
for label,stem in [('lifecycle','h3-live-a1200-fast-h3-candidate'),('clutch','controls-a1200-fast-h3-clutch'),('manual','drive-manual-a1200-fast-h3-manual'),('040-mmu-32m','controls-a1200-fast-h3-040-mmu-32m')]:
 p=r/f'tmp/step5/c4-q03-{stem}/result.json';j=read(p);key='manual_controls_status' if label=='manual' else 'status';assert j[key]=='passed',(label,j.get(key))
 if label=='lifecycle':
  assert j['road_workspace_reset_after_reload'] and j['pause_exact_debt_preserved'] and j['ledger_restored_words']>0
  snapshots=[v for v in j.values() if isinstance(v,dict) and 'intena' in v];assert len(snapshots)>=20 and len({v['intena'] for v in snapshots})==1 and all(v['owned']==0 for v in snapshots)
 report['controls'][label]=evidence(p)
p=r/'tmp/step5/c4-q03-h3-bad-signature-a1200-fast-candidate/result.json';j=read(p);assert j['status']=='passed' and j['colour_hook_not_installed'];report['failure_cleanup']=evidence(p)
report['deferred']=['Human full-race playtesting','Real Amiga hardware qualification','Repackaging/releasing a successor to unchanged RC2']
report['harness']=[evidence(p) for p in sorted((r/'tools').glob('*h3*.py'))]
(r/'manifest/render-h3-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('H3 acceptance evidence verified')
