#!/usr/bin/env python3
"""Capture sampled fields in separate chunks under FS-UAE's 100-field per-command limit.
Use immediately after quick_start (paused). Existing partial traces are rejected.
"""
import argparse,os,struct,socket,json
from pathlib import Path
import _amigaxdev  # noqa: F401
from amigaxdev import barto
ROOT=Path(__file__).resolve().parents[1]
SOCK=ROOT/'tmp/run'/(os.environ.get('INSTANCE') or 'default')/'.run/driving.sock'
# macOS limits a socket path to 104 bytes: a deep checkout connects by the relative path.
if len(str(SOCK))>100:SOCK=Path(os.path.relpath(SOCK))
def command(s):
 with socket.socket(socket.AF_UNIX) as c:
  c.settimeout(1800);c.connect(str(SOCK));c.sendall(s.encode());out=b''
  while b:=c.recv(65536):out+=b
 ans=out.decode()
 if ans.startswith('ERROR'):raise RuntimeError(ans)
 return ans

def header_end(data):
 nsec=struct.unpack_from('<I',data,4)[0];off=8+4*nsec+16
 for _ in range(3):off+=4+struct.unpack_from('<I',data,off)[0]
 return off+8

def combine(parts,target,total):
 # Preserve the initial snapshots; each following record has its own custom/DMA state.
 with target.open('xb') as out:
  for idx,p in enumerate(parts):
   t=barto.load(p);end=header_end(t.data)
   if idx==0:out.write(struct.pack('<I',total));out.write(t.data[4:end])
   out.write(t.data[end:])
 assert len(barto.load(target).fields)==total

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--fields',type=int,default=250);p.add_argument('--continue-existing-100',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 assert a.fields>0
 cap=a.capture.resolve();target=cap/'trace.bin';parts=[];remaining=a.fields
 if a.continue_existing_100:
  t=barto.load(target);assert len(t.fields)==100
  first=cap/'trace-part-0.bin';assert not first.exists();target.rename(first);parts.append(first);remaining-=100
 else:assert not target.exists(),'Use a fresh capture directory'
 command('stop')
 while remaining:
  n=min(100,remaining);part=cap/f'trace-part-{len(parts)}.bin';assert not part.exists()
  print(f'Capturing {n} PAL fields ({a.fields-remaining}/{a.fields})',flush=True)
  command(f'profile {n} {part}')
  t=barto.load(part);assert len(t.fields)==n,(len(t.fields),n)
  assert any(f.insn_end>f.insn_off for f in t.fields), "DMA-only capture: this CPU core emitted no instruction records; do not accept as an instruction profile"
  parts.append(part);remaining-=n
 combine(parts,target,a.fields)
 (cap/'capture.json').write_text(json.dumps({'fields':a.fields,'captured_seconds':a.fields/50,'continuous':len(parts)==1,'parts':[len(barto.load(x).fields) for x in parts]},indent=2)+'\n')
 for part in parts:part.unlink()
 print(f'Verified {a.fields} PAL fields in {target}')
if __name__=='__main__':main()
