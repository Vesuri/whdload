#!/usr/bin/env python3
"""Actual Installer 43.3 script-flow coverage with deterministic requester answers.
No host input automation; substitutes requesters only, keeps copy/icon/run logic.
"""
import hashlib,json,os,re,shutil,subprocess,time,socket
from pathlib import Path
from harness import ROOT,sha
from amigaxdev.gdbserve import Gdb
from amigaxdev import barto
from check_inputs import check
OUT=ROOT/'tmp/release-2.0b/installer-tests'
# The installer drawer as released: the original installer archive's drawer with the
# release/ files the package replaces.
SOURCE=OUT/'drawer'
def stage_drawer():
 shutil.copytree(ROOT/'tmp/game/TestDrive/TestDriveInstall',SOURCE)
 for n in ['Install','readme','TestDrive.inf']:shutil.copyfile(ROOT/'release'/n,SOURCE/n)
def form(text,start,replacement):
 a=text.index(start);depth=0;quoted=False;comment=False;i=a
 while i<len(text):
  c=text[i]
  if comment:
   if c=='\n':comment=False
  elif quoted:
   if c=='\\':i+=1
   elif c=='"':quoted=False
  elif c==';':comment=True
  elif c=='"':quoted=True
  elif c=='(':depth+=1
  elif c==')':
   depth-=1
   if depth==0:return text[:a]+replacement+text[i+1:]
  i+=1
 raise ValueError(start)
def main():
 check();OUT.mkdir();stage_drawer()
 installer=Path(os.environ['INSTALLER43']);binary=ROOT/'tmp/phase3/native-emulator/fs-uae'
 pin=ROOT/'manifest/release-2.0b-installer.json'
 inputs=[installer,binary,Path(os.environ['WORKBENCH_ADF']),Path(os.environ['KICKSTART']),Path(os.environ['WHDLOAD_BINARY'])]
 actual={str(p):sha(p) for p in inputs}
 pinned={str(ROOT/os.path.expandvars(k)):v for k,v in json.loads(pin.read_text()).items()};assert pinned==actual
 results=[]
 for mode,index in [('normal',0),('glow1',12),('glow2',13),('skip',0),('delete',0),('missing',0)]:
  base=OUT/mode;boot=base/'boot';parent=base/'Install with spaces';dest=parent/'TestDrive'
  for p in [boot/'s',boot/'env',boot/'Utilities',parent,base/'state']:p.mkdir(parents=True)
  for p in SOURCE.iterdir():
   if p.is_file():shutil.copyfile(p,boot/p.name)
  shutil.copyfile(ROOT/'tmp/build/release/TestDrive.Slave',boot/'TestDrive.Slave')
  shutil.copyfile(installer,boot/'Installer');shutil.copyfile(os.environ['WHDLOAD_BINARY'],boot/'WHDLoad')
  data=base/'disk';shutil.copytree(ROOT/'tmp/game/TestDrive_v1.3_0089/TestDrive/data',data)
  # The preinstalled archive omits original-disk C/S; authored copy fixtures.
  for folder in ['C','S']:
   (data/folder).mkdir();(data/folder/'copy-fixture').write_text('installer copy fixture '+folder)
  if mode=='missing':(data/'Devs/system-configuration').unlink()
  if mode in ('skip','delete'):
   dest.mkdir();(dest/'old-marker').write_text('existing')
  (parent/'unrelated').write_text('keep')
  # Viewer stubs avoid UI; real run/fallback remains exercised.
  for n,rc in [('Multiview',20),('More',0)]:
   (boot/'Utilities'/n).write_text('.key FILE/A\nEcho "<FILE>" >DH2:'+n+'-readme\nQuit '+str(rc)+'\n')
  s=(SOURCE/'Install').read_text(encoding='latin1')
  s='(if 0 (welcome))\n'+s
  s=form(s,'(message\n      (cat\n        "Warning:', '("legacy Installer warning acknowledged")')
  s=s.replace('SYS:Utilities/Multiview','Execute SYS:Utilities/Multiview').replace('SYS:Utilities/More','Execute SYS:Utilities/More')
  s=form(s,'(askdir\n    (prompt', '"DH2:Install with spaces"')
  s=form(s,'(askchoice\n\t(prompt "In which form', '0')
  s=form(s,'(askdisk\n        (dest #AD_disk)', '("disk already assigned")')
  s=form(s,'(askchoice\n        (prompt ("\\nWhich %s icon',str(index))
  s=form(s,'(askbool\n      (prompt',str(int(mode=='delete')))
  s=form(s,'(abort "The disk is missing', '((textfile (dest "DH2:missing-rejected") (append "yes")) (exit (quiet)))')
  s=s.replace('(exit)','(exit (quiet))')
  (boot/'Install').write_text(s,encoding='latin1')
  (boot/'s/startup-sequence').write_text('CD DH0:\nStack 32768\nDF0:C/Assign C: DF0:C\nDF0:C/Assign LIBS: DF0:Libs\nDF0:C/Assign ENV: RAM:\nDF0:C/Assign ENVARC: DH0:env\nDF0:C/Assign T: RAM:\nDF0:C/Assign "TEST DRIVE:" DH2:disk\nPath DH0: ADD\nC:LoadWB\nInstaller SCRIPT DH0:Install APPNAME "Test Drive" MINUSER NOVICE DEFUSER NOVICE LOGFILE DH2:installer.log NOPRETEND >DH2:console.log\nEcho done >DH2:finished\n')
  port_socket=socket.socket();port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1];port_socket.close()
  with (base/'emulator.log').open('w') as log:
   proc=subprocess.Popen([str(binary),'--remote_debugger=20','--remote_debugger_port='+str(port),'--amiga_model=A1200','--chip_memory=2048','--fast_memory=8192','--kickstart_file='+os.environ['KICKSTART'],'--hard_drive_0='+str(boot),'--hard_drive_0_priority=10','--hard_drive_2='+str(base),'--floppy_drive_0='+os.environ['WORKBENCH_ADF'],'--warp_mode=1','--fullscreen=0','--state_dir='+str(base/'state')],stdout=log,stderr=log)
   g=None
   try:
    time.sleep(2);g=Gdb(port,str(base),'INSTALLER_READY');g.cont()
    end=time.monotonic()+30
    while not (base/'finished').exists() and time.monotonic()<end:
     assert proc.poll() is None,'emulator exited';time.sleep(.25)
    if not (base/'finished').exists():
     g.stop();trace=base/'failure.bin';g.cmd(f'monitor profile 1 \"\" \"{trace}\"');(base/'failure.png').write_bytes(barto.load(trace).fields[-1].shot)
    assert (base/'finished').exists(),f'Installer did not finish: {base}'
    assert (base/'More-readme').exists(),'viewer fallback missing'
    if mode=='missing':assert (base/'missing-rejected').exists()
    else:
     for n in ['Cars','Pics','Songs','DEVS','C','S','Sfx','HighScores','cars.txt']:
      original=next(p for p in data.iterdir() if p.name.lower()==n.lower())
      copied=next(p for p in (dest/'data').iterdir() if p.name.lower()==n.lower())
      if original.is_dir():
       for f in original.rglob('*'):
        if f.is_file():assert (copied/f.relative_to(original)).read_bytes()==f.read_bytes(),str(f)
      else:assert copied.read_bytes()==original.read_bytes()
     for n in ['readme','Instructions','TD']:
      target=dest/'data'/n if n=='TD' else dest/n
      assert target.read_bytes()==(SOURCE/n).read_bytes(),n
     for n in ['readme.info','Instructions.info']:
      before=(SOURCE/n).read_bytes();after=(dest/n).read_bytes()
      # OS 3.1 icon.library rewrites pointer fields and drops the OS 3.5 tail.
      a=bytearray(before[:len(after)]);b=bytearray(after)
      for lo,hi in [(22,26),(50,66),(88,92)]:a[lo:hi]=b'\0'*(hi-lo);b[lo:hi]=b'\0'*(hi-lo)
      assert a==b,n
     assert (dest/'TestDrive.Slave').read_bytes()==(ROOT/'tmp/build/release/TestDrive.Slave').read_bytes()
     expected={'cars','pics','songs','devs','c','s','sfx','highscores','cars.txt','td'}
     assert {p.name.lower() for p in (dest/'data').iterdir() if not p.name.endswith('.uaem')}==expected
     icon=(dest/'TestDrive.info').read_bytes();assert b'WHDLoad' in icon
     assert (b'CUSTOM2=1' in icon)==(index==0)
     assert (dest/'old-marker').exists()==(mode=='skip')
    assert (parent/'unrelated').read_text()=='keep'
    results.append(dict(mode=mode,status='PASS'));print(mode+': PASS',flush=True)
   finally:
    if g:
     g.p.terminate();g.p.wait(timeout=5)
    proc.terminate()
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:proc.kill();proc.wait()
 (OUT/'report.json').write_text(json.dumps(dict(scope='Installer 43.3 with deterministic requester answers, not interactive requester coverage',script_sha256=sha(SOURCE/'Install'),results=results),indent=2)+'\n')
if __name__=='__main__':main()
