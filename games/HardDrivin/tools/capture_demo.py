#!/usr/bin/env python3
"""Capture a calibrated attract window; trace 68000/020, count swaps on faster CPUs."""
import argparse,hashlib,json,os,shutil,socket,subprocess,sys,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
INSTANCE=os.environ.get('INSTANCE','');assert not INSTANCE or all(c.isalnum() or c in '_-' for c in INSTANCE)
RUN=ROOT/'tmp/run'/(INSTANCE or 'default')/'.run'
SOCK=RUN/'harddrivin.sock'
def command(s,timeout=1900):
 with socket.socket(socket.AF_UNIX) as c:
  c.settimeout(timeout);c.connect(str(SOCK));c.sendall(s.encode());parts=[]
  while part:=c.recv(65536):parts.append(part)
 reply=b''.join(parts).decode()
 if 'ERROR' in reply or 'No such file or directory' in reply:raise RuntimeError(reply)
 return reply

def sha(path):
 with open(path,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
 from capture_session import Session
 from machine_profiles import PROFILES
 from count_demo_swaps import count
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('out');p.add_argument('--profile',choices=PROFILES,default='a500');p.add_argument('--fields',type=int,default=1000);p.add_argument('--slave',type=Path);p.add_argument('--swap-only',action='store_true');a=p.parse_args();os.chdir(ROOT)
 assert a.fields>0
 out=Path(a.out).resolve();rel=out.relative_to(ROOT/'tmp/prof');assert not any(c.isspace() for c in str(rel));out.mkdir(parents=True,exist_ok=False)
 slave=a.slave.resolve() if a.slave else ROOT/'tmp/build/HardDrivin-verify.slave';shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10844)
 try:
  print('Calibrating',a.profile,flush=True);s.boot()
  if a.swap_only or s.env['SWAP_ONLY']=='1':
   result=count(s,a.fields);print({k:v for k,v in result.items() if k!='per_field'});return
  print(f'Capturing {a.fields} PAL fields; initial debugger attachment can take several minutes',flush=True)
  reply=command(f'profile {a.fields} {out}/trace.bin');(out/'capture-response.txt').write_text(reply)
  with (out/'trace.bin').open('rb') as f:assert struct.unpack('<I',f.read(4))[0]==a.fields
  s.dump_banks('after')
  if (RUN/'lldb-control.log').exists():shutil.copyfile(RUN/'lldb-control.log',out/'lldb-control.log')
  (out/'capture.json').write_text(json.dumps(dict(s.metadata,fields=a.fields,trace_sha256=sha(out/'trace.bin')),indent=2)+'\n')
  subprocess.run([sys.executable,str(ROOT/'tools/summarize_profile.py'),str(out/'trace.bin'),'--out',str(out)],check=True)
 finally:s.close()
if __name__=='__main__':main()
