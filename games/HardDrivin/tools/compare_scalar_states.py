import argparse,json,struct,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('candidate');p.add_argument('--reference',default='s3-stepinput-a500');a=p.parse_args();root=Path(__file__).resolve().parents[1]/'tmp/prof'
def read(name):
 path=root/name;m=json.loads((path/'metadata.json').read_text());raw=subprocess.check_output(['zstd','-qdc',str(path/'physics.bin.zst')]);size=m['snapshot_size'];out=[]
 for i in range(0,len(raw),size):
  b=bytearray(raw[i:i+size]);o=0x9940-0x8002;v=struct.unpack_from('>I',b,o)[0];struct.pack_into('>I',b,o,v-m['layout']['data_base']);out.append(bytes(b[0x98f6-0x8002:0x9952-0x8002]))
 return out
old=read(a.reference);new=read(a.candidate);diff=next((i for i,(x,y) in enumerate(zip(old,new)) if x!=y),None);r=dict(candidate=a.candidate,steps=min(len(old),len(new)),first_difference=diff,passed=len(new)==len(old) and diff is None)
if diff is not None:r['bytes']=[hex(0x98f6+i) for i,(x,y) in enumerate(zip(old[diff],new[diff])) if x!=y];r['old']=old[diff].hex();r['new']=new[diff].hex()
(root/a.candidate/'native-equivalence.json').write_text(json.dumps(r,indent=2)+'\n');print(r);assert r['passed']
