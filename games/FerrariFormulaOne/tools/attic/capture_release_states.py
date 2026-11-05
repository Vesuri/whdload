from pathlib import Path
import os,sys,time,signal,json,struct,hashlib
sys.path.insert(0,str(Path.home()/'.local/share/amiga/pylib'))
from amigaxdev.gdbserve import Server
r=Path(__file__).resolve().parents[1];os.chdir(r);profile=sys.argv[1] if len(sys.argv)>1 else 'a500';kind='release-state-'+os.environ.get('ARM','production');variant=os.environ.get('C1_VARIANT','candidate');name='c4-q03-'+kind+'-'+profile+'-'+variant;out=r/'tmp/step5'/name;out.mkdir(parents=True,exist_ok=True);arm=os.environ.get('ARM','production');b=r/'tmp/build/production-matched/FerrariFormulaOne.slave' if arm=='production' else r/('tmp/build/step5-c4-divide-frame-r3g-v1-ab/000/candidate.slave' if profile.startswith('a500') else 'tmp/build/step5-c2/020/candidate.slave' if profile=='a1200' else 'tmp/build/step5-b8-v3-source/lean/fine.slave');profiles=json.loads((r/'manifest/step3-profiles.json').read_text());runb=b
if arm=='accepted':
 raw=b.read_bytes();target=(r/'tmp/build/production-matched/FerrariFormulaOne.slave').read_bytes();code=bytearray(raw[32:-4]);assert len(raw)<=len(target);code+=bytes(len(target)-len(raw));header=bytearray(raw[:32]);struct.pack_into('>I',header,20,len(code)//4);struct.pack_into('>I',header,28,len(code)//4);runb=r/f'tmp/build/production-matched/accepted-{kind if False else profile}.slave';runb.write_bytes(header+code+bytes.fromhex('000003f2'))
os.environ.update(profiles[profile]);os.environ.update(json.loads(os.environ.get('RELEASE_PROFILE_OVERRIDES','{}')));os.environ.update(SLAVE=str(runb),WARP='1',WINDOW='none',JOY0='mouse',WHD_ARGS=os.environ.get('RELEASE_WHD_ARGS','CUSTOM1=1 CUSTOM2=1'),DETERMINISTIC='1',FSUAE=os.environ.get('RELEASE_FSUAE',str(r/'tmp/step5-frame-observer-build/fs-uae')),FF1_FRAME_SENTINEL='0',KICKSTART=os.environ['KICKSTART_A1200'] if not profile.startswith('a500') else os.environ['KICKSTART'])
s=Server('ff1measure',root=str(r),profile_window=False);log=[]
try:
 g=s.boot()
 def cmd(c):
  v=g.cmd(c,timeout=180);log.append(c+'\n'+v);(out/'live.log').write_text('\n'.join(log));return v
 def val(e):return int(cmd('p/x '+e).split('=')[-1].strip(),16)
 def dump(label):
  chip=int(os.environ['CHIP_KB'])*1024
  cmd(f'dump binary memory {out.relative_to(r)}/{label}.bin 0 {chip}')
  mem=(out/(label+'.bin')).read_bytes()
  for bank,base,key in [('fast',0x200000,'FAST_KB'),('slow',0xc00000,'SLOW_KB')]:
   size=int(os.environ[key])*1024
   if size:
    cmd(f'dump binary memory {out.relative_to(r)}/{label}-{bank}.bin {base} {base+size}')
    mem+=bytes(base-len(mem))+(out/(label+'-'+bank+'.bin')).read_bytes()
  return mem
 for boot_attempt in range(20):
  g.cont();time.sleep(1);g.stop()
  mem=dump('memory');u=lambda a:struct.unpack_from('>I',mem,a)[0]
  hits=[];at=0
  while True:
   at=mem.find(b'FF1B7PUBLICROOT',at)
   if at<0:break
   root=u(at-4)*4+4
   if 0<root<len(mem) and mem[root:root+2]==bytes.fromhex('6000'):hits.append((at,root))
   at+=1
  if hits:break
 assert len(hits)==1,hits
 marker,root=hits[0];table=u(root+16)*4;race=u(table+160*4)*4+4
 report=dict(root=hex(root),table=hex(table),race=hex(race),marker=hex(marker),pc=val('$pc'),slave_sha256=hashlib.sha256(runb.read_bytes()).hexdigest())
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)
 cmd('delete');cmd(f'break *{root+0x2e6}')
 cmd('condition $bpnum *(unsigned int*)$a3 == 0x22f30')
 assert 'Breakpoint' in cmd('continue')
 race=val('$d0+*(unsigned int*)($a3+28)')
 report['race']=hex(race);(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')

 import re
 kind='000' if profile.startswith('a500') else '020' if profile=='a1200' else 'fine'
 if arm=='production':
  build=json.loads((b.parent/'build.json').read_text());hs=build['host_symbols'];module=build['payloads'][kind];sy=module['symbols'];host=marker-hs['FF1PublicMarker'];probe=host+module['offset']
 else:
  def symbols(path):return {n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',path.read_text(errors='replace'),re.M)}
  hs=symbols(r/'tmp/build/step5-b7-loader-v3/build.list');sy=symbols(b.parent/'fine.list');host=marker-hs['FF1PublicMarker'];probe=host+len((r/'tmp/build/step5-b7-loader-v3/FerrariFormulaOne.slave').read_bytes())-36
 if arm=='accepted':module={'bytes':b.stat().st_size-36-(probe-host)}
 report.update(host=hex(host),probe=hex(probe),kind=kind,arm=arm)
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 cmd('delete')
 faults=['FF1WrongVersion'] if arm=='production' else []
 for n in faults:cmd(f'break *{host+hs[n]}')
 for n in (['C1Fault','velocity_stop'] if kind=='000' else ['C1Fault'] if kind=='020' else ['velocity_fault','schedule_bad']):
  if n in sy:cmd(f'break *{probe+sy[n]}')
 checkpoint=probe+sy['FF1PresentationAfterTick' if kind=='fine' else 'C1Checkpoint'];cmd(f'break *{checkpoint}')
 assert 'Breakpoint' in cmd('continue')
 report['stop_pc']=hex(val('$pc'));report['error']=val(f'*(unsigned int*){probe+sy["error"]}')
 if val('$pc')!=checkpoint:
  report['regs']=cmd('info registers');dump('fault');(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');raise AssertionError(report)
 ctx=probe+sy['schedule_context' if kind=='fine' else 'C1Context'];report['context_address']=hex(ctx)
 from step5_b7_addresses import Addresses
 memory=dump('anchor');addresses=Addresses(memory,table)
 blocks=json.loads((r/'manifest/step4-measurements.json').read_text())['semantic_blocks']+[dict(name='gear',address='0x6bf84',bytes=4),dict(name='instrument_phase',address='0x6c942',bytes=6),dict(name='instrument_rates',address='0x66c88',bytes=4),dict(name='flag_counter',address='0x66be0',bytes=2),dict(name='pit_flags',address='0xd0dc',bytes=8)]
 (out/'blocks.json').write_text(json.dumps(blocks,indent=2));(out/'addresses.json').write_text(json.dumps(addresses.rows,indent=2))
 # Read the live game/engine span, avoiding ten megabytes of unrelated RAM
 # at every halted update. Cross-check this observation at both endpoints.
 sample_ranges=[]
 for lo,hi in sorted([(table,table+209*4),(probe,probe+module['bytes'])]+[(x['actual']-8,x['actual']+x['size']) for x in addresses.rows]):
  if sample_ranges and lo<=sample_ranges[-1][1]+65536:sample_ranges[-1][1]=max(sample_ranges[-1][1],hi)
  else:sample_ranges.append([lo,hi])
 sample_base=bytes(memory)
 def sample_memory():
  fresh=bytearray(sample_base)
  for i,(lo,hi) in enumerate(sample_ranges):
   path=out/f'sample-span-{i}.bin';cmd(f'dump binary memory {path.relative_to(r)} {lo} {hi}');fresh[lo:hi]=path.read_bytes()
  return fresh
 def record_bytes(m):
  canonical=addresses.canonical_memory(m)
  return b''.join(canonical[int(x['address'],16):int(x['address'],16)+x['bytes']] for x in blocks)
 report['sample_ranges']=sample_ranges;report['sample_endpoint_checks']=[]
 records=[];private=[]
 cmd('monitor warp 0')
 for step in range(100):
  if step:assert 'Breakpoint' in cmd('continue')
  memory=sample_memory();record=record_bytes(memory)
  if step in (0,99):
   full=dump('sample-full-check');assert record_bytes(full)==record
   assert full[probe:probe+module['bytes']]==memory[probe:probe+module['bytes']]
   report['sample_endpoint_checks'].append(step+1)
  records.append(record)
  if kind=='fine':
   private.append({n:memory[probe+sy[n]:probe+sy[n]+size].hex() for n,size in [('velocity_shadow',12),('position_shadow',12),('heading_shadow',12),('speed_shadow',6),('steering_shadow',18),('wear_remainders',8),('fuel_remainders',2)]})
  if step%25==0:print(profile,arm,step,flush=True)
 (out/'records.bin').write_bytes(b''.join(records));(out/'private.json').write_text(json.dumps(private))
 report['context_after']=list(struct.unpack_from('>14I',memory,ctx));report['error']=val(f'*(unsigned int*){probe+sy["error"]}');report['status']='captured';report['steps']=100
 (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(report,flush=True)

finally:
 (out/'capture.log').write_text('\n'.join(log))
 if s.g:s.g.p.kill()
 try:os.kill(int((r/'amiga/.run/fsuae.pid').read_text()),signal.SIGKILL)
 except (ProcessLookupError,FileNotFoundError):pass
