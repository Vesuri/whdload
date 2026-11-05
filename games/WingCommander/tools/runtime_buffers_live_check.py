#!/usr/bin/env python3
"""Observe workspace initialization at the real WHDLoad loader handoff."""
import argparse,json,os,re,subprocess,time
from pathlib import Path
import _amigaxdev
from amigaxdev.gdbserve import Server
from ocs_reconstruct import ROOT,new_output
from runtime_buffers import load


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('variant',choices=('ocs','cd32'));p.add_argument('build',type=Path)
 p.add_argument('--output',required=True);a=p.parse_args();out=new_output(a.output);out.mkdir(parents=True)
 ocs=a.variant=='ocs'
 if ocs:from ocs_runtime import locate
 else:from cd32_runtime import locate
 meta=json.loads((a.build/'build.json').read_text())
 name='WingCommander.Slave' if ocs else 'WingCommanderCD32.Slave'
 slave=a.build/name;image=load(slave.read_bytes())
 original=ROOT/('tmp/originals/ocs/WingCommander/WingCommander.Slave' if ocs else 'tmp/originals/cd32/WingCommanderCD32/WingCommanderCD32.Slave')
 entry=int.from_bytes(original.read_bytes()[56:58],'big')
 env=dict(os.environ,SLAVE=str(slave.resolve()),WC_VARIANT=a.variant,
          FSUAE_RUN='../'+str(out.relative_to(ROOT))+'/run',WARP='1',NTSC='0',WINDOW='front',
          JOY0='none',JOY1='none',DETERMINISTIC='1',AMIGA_SETUP='a1200-030',
          WHD_ARGS=('CUSTOM5=1' if ocs else 'CUSTOM5=0')+' DCACHE',
          WC_BASELINE_CACHE_MODEL='1',EXTRA_ARGS='')
 g=None
 def stop():
  nonlocal g
  if g:g.p.kill();g=None
  subprocess.run(['/bin/bash',str(ROOT/'amiga/run.sh'),'stop'],env=env,check=True)
 def boot():return Server('wc-workspace',root=str(ROOT),run_dir='amiga/'+env['FSUAE_RUN'],profile_window=False).boot(env)
 def cmd(s):
  result=g.cmd(s,timeout=60)
  if any(x in result for x in ('Cannot access','Remote connection closed','Error')):raise ValueError(result)
  return result
 try:
  g=boot();snapshot=out/'calibration.bin'
  for _ in range(45):
   g.cont();time.sleep(1);g.stop()
   cmd(f'dump binary memory {snapshot.relative_to(ROOT)} 0x200000 0xa00000')
   try:layout=locate(snapshot.read_bytes());break
   except ValueError:pass
  else:raise ValueError('game not reached during calibration')
  snapshot.unlink();stop();g=boot();base=layout['slave']
  result=cmd(f'break *{base+entry:#x}\ncontinue\ndelete')
  assert 'Breakpoint' in result,result
  path=out/'workspace.bin';start=meta['initialized_bytes']
  cmd(f'dump binary memory {path.relative_to(ROOT)} {base+start:#x} {base+len(image):#x}')
  data=path.read_bytes();assert len(data)==meta['runtime_workspace_bytes'] and not any(data)
  path.unlink()
  # Continue through the ordinary loader to its native game entry, establishing
  # the wrapper's handoff as well as observing the freshly cleared allocation.
  h0=layout['hunks'][0]
  result=cmd(f'break *{h0:#x}\ncontinue\ndelete')
  assert 'Breakpoint' in result,result
  (out/'report.json').write_text(json.dumps(dict(passed=True,variant=a.variant,
    slave_sha256=meta['sha256'],stored_bytes=slave.stat().st_size,
    allocated_bytes=len(image),zero_workspace_bytes=len(data),native_game_entry=True,
    machine='a1200-030',scope='WHDLoad allocation and startup; no gameplay or performance claim'),indent=2)+'\n')
  print('PASS:',a.variant,'real WHDLoad workspace and native game entry')
 finally:stop()

if __name__=='__main__':main()
