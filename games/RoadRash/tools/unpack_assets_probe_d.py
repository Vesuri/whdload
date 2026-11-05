import sys,json
from harness_a import *
s=Session(sys.argv[1])
try:
 names=json.loads((ROOT/'tmp/d-unpack-assets-files.json').read_text())
 for i in range(80):
  s.cmd('monitor fields 99',timeout=120)
  paths=list((s.run/'dh1/data').glob('_audit_*.bin'))
  if len(paths)==len(names):break
 else:s.shot('failed.png');raise RuntimeError(f'only {len(paths)} unpacked files')
 dest=s.out/'unpacked';dest.mkdir();rows=[]
 for i,n in enumerate(names):
  data=(s.run/f'dh1/data/_audit_{i:02d}.bin').read_bytes();(dest/n).write_bytes(data);rows.append(dict(name=n,size=len(data),first32=data[:32].hex()))
 (s.out/'files.json').write_text(json.dumps(rows,indent=2)+'\n');print('unpacked',len(rows),flush=True)
finally:s.quit()
