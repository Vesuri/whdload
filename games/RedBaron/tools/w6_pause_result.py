import argparse,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    found=re.match(r'00:([0-9A-F]+)\s',following)
    if found:return int(found[1],16)
 raise ValueError(name)
slave=m['entry']['game_anchor']-symbol('tape_game_anchor')
banks=[(int(p.stem.split('-')[1],16),p.read_bytes()) for p in a.capture.glob('audit-*.bin')]
def read(addr,n):
 for base,b in banks:
  off=addr-base
  if 0<=off and off+n<=len(b):return b[off:off+n]
 raise ValueError(hex(addr))
assert read(slave+symbol('tape_marker'),8)==b'RBVERIFY'
result={name:int.from_bytes(read(slave+symbol(name),4),'big') for name in ['time_core_result','time_input_test_result','time_pause_test_result']}
assert list(result.values())==[426,512,1],result
result['sha256']=m['slave_sha256'];(a.capture/'selftest-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
