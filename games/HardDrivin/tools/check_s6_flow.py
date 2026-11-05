import os,sys,json,re,shutil,struct,time
from pathlib import Path
from capture_demo import ROOT,command,RUN,sha
from capture_session import Session
name,profile=sys.argv[1:];os.chdir(ROOT);out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=False)
for ext in ['slave','lst']:shutil.copyfile(ROOT/'tmp/build'/('s6-flow.'+ext),out/('slave.'+ext))
s=Session(out,profile,out/'slave.slave',0x10ed4);s.env['WHD_ARGS']+=' CUSTOM1=1 '+os.environ.get('FLOW_STORAGE','WRITEDELAY=0 NOWRITECACHE');s.env['SWAP_ONLY']='1'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];listing=(out/'slave.lst').read_text(encoding='latin1')
 sym=lambda n:int(re.search(r'^'+re.escape(n)+r'\s+00:([0-9A-Fa-f]+)',listing,re.M)[1],16)
 slave=s.layout['published']-sym('_code_start');points={'REPLAY':base+0x10b08,'GAMEOVER':base+0x10f62,'NAME':slave+sym('_hiscore_save_v1'),'SAVE':slave+sym('_hss_main'),'EXIT':slave+sym('_exit')}
 call=int(re.search(r'^00:([0-9A-F]+).*jsr\s+resload_SaveFile\(a2\)',listing,re.M)[1],16)
 points['WRITE_IN']=slave+call;points['WRITE_OUT']=slave+call+4
 field=slave+sym('_verify_drive_state')+4
 lines=['gdb break *'+hex(next(iter(points.values())))]+['break *'+hex(v) for v in list(points.values())[1:]]+[f'break *{base+0x10f28:#x}','set $done=0','set $frames=0','set $crash=0','while $done==0 && $frames<12000','continue']
 lines += [f'if $pc=={base+0x10f28:#x}','set $frames=$frames+1',f'if *(unsigned char*){a4-0x69fa:#x} != 0','set $crash=$crash+1','end','end']
 for tag,addr in points.items():
  lines += [f'if $pc=={addr:#x}',f'printf "EVENT {tag} %u\\n",*(unsigned int*){field:#x}']
  if tag in ['WRITE_IN','WRITE_OUT']:lines+=['printf \"WRITE %u %u %u %u\\n\",$d0,$d1,$a0,$a1']
  if tag=='EXIT':lines+=['set $done=1']
  lines+=['end']
 lines+=['end','printf "COUNTS %u %u\\n",$frames,$crash','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 events=[(t,int(v)) for t,v in re.findall(r'^EVENT (\w+) (\d+)$',reply,re.M)];counts=list(map(int,re.search(r'^COUNTS (\d+) (\d+)$',reply,re.M).groups()))
 assert all(t in [x[0] for x in events] for t in points),events
 assert counts[1]>0,counts
 (out/'dump-response.txt').write_text(command(f'gdb dump binary memory {out.relative_to(ROOT)}/hiscore-plain.bin {a4-0x64de:#x} {a4-0x64de+380:#x}'))
 assert (out/'hiscore-plain.bin').stat().st_size==380
 (out/'continue-response.txt').write_text(command('cont',timeout=60))
 saved=RUN/'dh1/data/hiscore.dat'
 deadline=time.monotonic()+90
 while not saved.exists() and time.monotonic()<deadline:
  alternate=RUN/'dh1/hiscore.dat'
  if alternate.exists():saved=alternate;break
  time.sleep(1)
 if not saved.exists():
  (out/'exit-registers.txt').write_text(command('stop'))
  (out/'screenshot-response.txt').write_text(command('shot '+str(out/'exit.png')))
 assert saved.exists() and saved.stat().st_size==380
 shutil.copyfile(saved,out/'hiscore-saved.bin')
 # Original byte-wise EOR encryption is checked after native save and decrypt.
 plain=(out/'hiscore-plain.bin').read_bytes();encrypted=saved.read_bytes()
 key=0x2a113417;expected=bytearray()
 for i,v in enumerate(plain):
  n=379-i;expected.append(v^(key&255));key^=n
  shift=n&31
  if shift:key=((key>>shift)|(key<<(32-shift)))&0xffffffff
 assert encrypted==bytes(expected)
 r=dict(passed=True,profile=profile,events=events,physics_returns=counts[0],crash_returns=counts[1],saved_bytes=len(encrypted),saved_sha256=sha(saved))
 (out/'results.json').write_text(json.dumps(r,indent=2)+'\n');print(r,flush=True)
finally:s.close()
