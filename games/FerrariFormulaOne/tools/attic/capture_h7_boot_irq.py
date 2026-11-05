from pathlib import Path
import os,sys,json,time,struct,signal
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1];out=r/f'tmp/step5/h7-boot-irq-{profile}';out.mkdir(parents=True,exist_ok=True)
b=r/'tmp/build/render-h6';ref=json.loads((r/f'tmp/step5/c4-q03-h5-fps-{profile}-h6-normal/result.json').read_text());build=json.loads((b/'build.json').read_text());hs=build['host_symbols'];sy=build['payloads']['fine']['symbols'];host=int(ref['host'],16);probe=int(ref['probe'],16);checkpoint=probe+sy['FF1PresentationAfterTick']
os.environ.update(json.loads((r/'manifest/step3-profiles.json').read_text())[profile]);os.environ.update(SLAVE=str(b/'FerrariFormulaOne.slave'),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache',DETERMINISTIC='1',FSUAE=str(r/'tmp/step5-frame-observer-build/fs-uae'),KICKSTART=os.environ['KICKSTART_A1200'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[];report={'profile':profile,'transitions':[]}
try:
 g=s.boot()
 def cmd(x):
  v=g.cmd(x,timeout=180);log.append(x+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(x):return int(cmd('p/x '+x).split('=')[-1].strip(),16)
 initial=val('*(unsigned short*)0xdff01c')&64
 cmd(f'set $blitlast={initial}');cmd('awatch -l *(unsigned short*)0xdff09a');cmd('condition $bpnum ((*(unsigned short*)0xdff01c ^ $blitlast) & 64) != 0');cmd(f'break *{checkpoint}')
 for i in range(80):
  reply=cmd('continue');pc=val('$pc');ena=val('*(unsigned short*)0xdff01c')
  if pc==checkpoint:break
  report['transitions'].append(dict(pc=hex(pc),intena=hex(ena),registers=cmd('info registers'),code=cmd('x/32hx $pc-32'),stack=cmd('x/12wx $sp')))
  cmd(f'set $blitlast={ena&64}');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 else:raise AssertionError('transition budget')
 report['entry_intena']=hex(ena);report['entry_pc']=hex(pc);report['status']='passed'
 cmd('dump binary memory '+str(out/'entry-chip.bin')+' 0 0x200000')
 cmd('dump binary memory '+str(out/'entry-fast.bin')+' 0x200000 '+hex(0x200000+int(os.environ['FAST_KB'])*1024))
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
