"""Check render patches against native bytes or existing slave wait-site patches."""
import sys,re,json,struct
from pathlib import Path
from game_image import hunks
p=Path(sys.argv[1]);m=json.loads((p/'metadata.json').read_text());lst=(p/'slave.lst').read_text(encoding='latin1');sym=lambda n:int(re.search(r'^'+n+r'\s+00:([0-9A-Fa-f]+)',lst,re.M)[1],16);slave=m['layout']['published']-sym('_code_start');live=(p/'game-code.bin').read_bytes();opts=m['render_window']['custom3'];ct2=m['render_window'].get('custom2',0);ct1=m['render_window'].get('custom1',0);original=hunks()[0]['data'];checks=[]
for off,gate,name in [(0x2a2e,2,'_render_rotate_y'),(0x2a7a,2,'_render_rotate_x')]:
 expected=bytes.fromhex('4ef9')+struct.pack('>I',slave+sym(name))+bytes.fromhex('4e71') if opts&gate else original[off:off+8]
 assert live[off:off+8]==expected,(hex(off),expected.hex(),live[off:off+8].hex());checks.append(hex(off))
if re.search(r'^_render_wait\s',lst,re.M):
 name='_render_wait' if opts&4 and (ct2==0 or ct1) else '_blitwait';target=slave+sym(name)
 for off in [0x141c,0x143c,0x14fe,0x151e,0x15b4,0x15ce,0x1774,0x17a6,0x17e0,0x795c,0x799a]:
  expected=bytes.fromhex('4eb9')+struct.pack('>I',target)+bytes.fromhex('4e714e71');assert live[off:off+10]==expected,(hex(off),live[off:off+10].hex(),expected.hex());checks.append(hex(off))
r=dict(passed=True,custom3=opts,custom2=ct2,checked_sites=checks,slave_sha256=m['slave_sha256'],scope='Rotation sites compared with pristine bytes when off; eleven wait sites compared with original-slave helper target when off or nonzero CUSTOM2 with CUSTOM1=0, new helper when on.')
(p/'render-patches.json').write_text(json.dumps(r,indent=2)+'\n');print(p.name,len(checks),'PASS')
