"""Boot the normal slave and inspect initialized player options without a tape."""
import json,os,re,struct,subprocess,sys,time,hashlib
from pathlib import Path
import route_status as r
sys.path.insert(0,str(r.ROOT/'tools'))
from hunks import read_hunks
build=Path('tmp/w5-player-build');slave=(build/'normal.slave').resolve();listing=(build/'normal.lst').read_text(encoding='latin1')
def label(n):return int(re.search(r'^'+n+r'\s+00:([0-9a-fA-F]+)',listing,re.M)[1],16)
text=read_hunks(slave.read_bytes())[0].data
needle=b'Red Baron: unexpected sim v1 performance hook bytes';marker=text.index(needle)
for machine in ('a500','020','030'):
 for option in ((None,0,1) if machine=='a500' else (0,1)):
  requested=0 if option is None else option
  out=Path(f'tmp/prof/w5-player-{machine}-{option}');assert not out.exists();out.mkdir()
  meta=json.loads(Path(('tmp/prof/w2-combined-030-0-r2/entry.json' if machine=='030' else f'tmp/prof/w2-combined-{machine}-0/entry.json')).read_text())
  pid=(r.ROOT/'tmp/run/default/.run/fsuae.pid').read_text().strip();p=subprocess.run(['ps','-p',pid,'-o','command='],capture_output=True,text=True)
  if p.returncode==0:assert f'--base_dir={r.ROOT/"tmp/run/default/.run/fsuae"}' in p.stdout
  try:r.command('quit')
  except (ConnectionRefusedError,FileNotFoundError):pass
  env=dict(os.environ,MallocScribble='1',SLAVE=str(slave),WARP='1',DETERMINISTIC='1',JOY0='none',JOY0_MODE='nothing',JOY1='none',CPU=meta['cpu'],CHIP_KB=meta['chip_kb'],FAST_KB=meta['fast_kb'],EXTRA_ARGS=meta['extra_args'],WHD_ARGS=('' if option is None else f'CUSTOM2={option}')+(' MMU' if machine=='030' else ''),AMIGA_MODEL='A1200' if machine=='020' else 'A500')
  env.pop('BOOT_BREAK',None)
  if machine=='020':env['KICKSTART']=os.environ['KICKSTART_A1200']
  with (out/'serve.log').open('w') as log:server=subprocess.Popen([sys.executable,'tools/redbaron.py','serve'],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  expected=0 if requested==0 else (4026 if machine=='030' else 8127)
  deadline=time.monotonic()+120;found=[]
  while time.monotonic()<deadline:
   if server.poll() is not None:raise RuntimeError('Server exited')
   try:
    r.command('stop');found=[]
    for lo,hi in r.memory_regions():
     f=out/f'memory-{lo:x}.bin';r.command(f'gdb dump binary memory {f} {lo:#x} {hi:#x}');b=f.read_bytes();start=0
     while True:
      at=b.find(needle,start)
      if at<0:break
      start=at+1;base=at-marker
      if base<0:continue
      def value(n):return struct.unpack_from('>I',b,base+label(n))[0]
      if value('_resload'):
       found.append(dict(slave_base=lo+base,custom2=value('perf_custom2'),attnflags=value('perf_attnflags'),mask=value('perf_mask')))
    if len(found)==1 and found[0]['custom2']==requested and found[0]['mask']==expected:break
    r.command('cont')
   except (FileNotFoundError,ConnectionRefusedError):pass
   time.sleep(.5)
  assert len(found)==1,found
  result=found[0];expected=0 if requested==0 else (4026 if machine=='030' else 8127)
  assert result['custom2']==requested and result['mask']==expected,result
  result.update(machine=machine,option=option,expected_mask=expected,sha256=hashlib.sha256(slave.read_bytes()).hexdigest())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');(out/'slave.slave').write_bytes(slave.read_bytes());(out/'slave.lst').write_text(listing)
  (out/'debug.uae').write_bytes((r.ROOT/'tmp/run/default/.run/fsuae/Cache/Logs/debug.uae').read_bytes())
  print('PLAYER OPTIONS PASS',result,flush=True)
