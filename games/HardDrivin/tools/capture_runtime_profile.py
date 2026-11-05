"""Read-only 500-field gameplay profile of a gated development slave."""
import argparse,json,os,shutil,struct,subprocess,sys
from capture_demo import ROOT,command,sha,RUN
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--slave',required=True);p.add_argument('--custom1',type=int,default=1);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave')
s=Session(out,'a500',out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();s.dump_banks('before');print('Capturing 500 fields',flush=True)
 reply=command(f'profile 500 {out}/trace.bin');(out/'capture-response.txt').write_text(reply)
 with (out/'trace.bin').open('rb') as f:assert struct.unpack('<I',f.read(4))[0]==500
 s.dump_banks('after')
 if (RUN/'lldb-control.log').exists():shutil.copyfile(RUN/'lldb-control.log',out/'lldb-control.log')
 (out/'capture.json').write_text(json.dumps(dict(s.metadata,fields=500,trace_sha256=sha(out/'trace.bin')),indent=2)+'\n')
finally:s.close()
subprocess.run([sys.executable,str(ROOT/'tools/summarize_profile.py'),str(out/'trace.bin'),'--out',str(out)],check=True)
