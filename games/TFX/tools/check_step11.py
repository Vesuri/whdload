"""Check retained rejection evidence and unchanged release bytes; no state waiver."""
from pathlib import Path
import json,csv,re,hashlib,subprocess,sys
root=Path(__file__).resolve().parents[1];p=root/'tmp/step11';dev=root
def sha(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def check_case(name):
 on=p/name;off=p/(name+'-off');listing=p/(name+'.lst')
 for d in [on,off]:subprocess.run([sys.executable,str(dev/'tools/step11_report.py'),str(d),str(listing)],check=True,stdout=subprocess.DEVNULL)
 a=json.loads((on/'step11-report.json').read_text());b=json.loads((off/'step11-report.json').read_text())
 assert sha(on/'slave.slave')==sha(off/'slave.slave')
 assert a['strict_fpu']==b['strict_fpu']==1
 assert a['fpu_exceptions']==b['fpu_exceptions']==0
 assert not any(a['cache'].values()) and not any(b['cache'].values())
 assert a['publications']==b['publications']==73
 mode=json.loads((off/'copy-mode.json').read_text());assert mode['forced_off']
 branch=(off/'copy-branch.bin').read_bytes();assert branch[0]==0x67
 assert (off/'copy-branch-off.bin').read_bytes()==bytes([0x60,branch[1]])
 # Candidate instructions really execute on the on side, and never on the off side.
 text=listing.read_text(encoding='latin1')
 if name=='move16':pattern=r'^00:([0-9A-F]+) F6218000'
 elif name=='movem':pattern=r'^00:([0-9A-F]+) 4CD602FE' # actual listing verified below
 else:pattern=None
 sb=a['slave_base'];sb2=b['slave_base']
 def pcs(d):return {int(r[1]):int(r[2]) for r in csv.reader((d/'profile.csv').open()) if r[0]=='pc'}
 ap,bp=pcs(on),pcs(off)
 if name=='movem':matches=re.findall(r'^00:([0-9A-F]+) [0-9A-F ]+\s+\d+:\s+movem.l \(a1\)\+,d1-d7/a2',text,re.M)
 elif pattern:matches=re.findall(pattern,text,re.M)
 else:
  # First instruction after candidate loop count: guard branch ends before it.
  matches=[]
  lines=text.splitlines();inside=False
  for line in lines:
   if 'rept 16' in line:inside=True
   m=re.match(r'^00:([0-9A-F]+) 20D9',line)
   if inside and m:matches.append(m[1])
   if inside and 'dbf     d0,.copy040' in line:break
 assert matches,(name,'missing instruction anchors')
 for m in matches:assert ap.get(sb+int(m,16),0)>0 and bp.get(sb2+int(m,16),0)==0,(name,m)
 return dict(on=a['publications'],off=b['publications'],candidate_instructions_verified=len(matches),on_image_equals_off=(on/'after.png').read_bytes()==(off/'after.png').read_bytes(),raw_hunks_equal=all((on/f'end-hunk{i}.bin').read_bytes()==(off/f'end-hunk{i}.bin').read_bytes() for i in range(3)),on_copy_percent=next(x['percent'] for x in a['regions'] if x['name']=='slave screen copy/publication'),off_copy_percent=next(x['percent'] for x in b['regions'] if x['name']=='slave screen copy/publication'))
results={n:check_case(n) for n in ['move16','movem','unrolled']}
assert all(json.loads((p/'baseline-repeat.json').read_text()).values())
assert sha(dev/'tmp/build/release/TFX.Slave')==sha(p/'baseline.slave')
for n in ['fpsp040','fpsp060']:assert sha(dev/'tmp/build'/n)==sha(p/'baseline'/n)
assert subprocess.check_output(['git','diff','--','src/TFXHD.s'],cwd=root)==b''
(p/'validation.json').write_text(json.dumps(dict(candidates=results,release_unchanged=True,baseline_repeated=True),indent=2));print(json.dumps(results,indent=2))
