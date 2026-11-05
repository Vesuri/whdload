"""Private counterfactual: record or replay native main-context BCD clock observations."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,struct
from capture_demo import ROOT,command,sha
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('name');p.add_argument('--slave',default='s3-stepinput.slave');p.add_argument('--custom1',type=int,default=0);p.add_argument('--steps',type=int,default=108);p.add_argument('--world',action='store_true');p.add_argument('--delay',type=int,default=0);p.add_argument('--clock-replay',type=Path);a=p.parse_args();clock_tape=json.loads(a.clock_replay.read_text()) if a.clock_replay else None;clock_tape_sha=sha(a.clock_replay) if a.clock_replay else None;os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);slave=ROOT/'tmp/build'/a.slave;shutil.copyfile(slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 print(a.name,flush=True);s.boot();base=s.layout['code_base'];a4=s.layout['a4'];regions=s.layout['regions'][1:];size=sum(r['size'] for r in regions)
 world=[]
 if a.world:
  banks=s.dump_banks('world-layout')
  def mem(addr,n):
   for b,x in banks:
    if b<=addr and addr+n<=b+len(x):return x[addr-b:addr-b+n]
   raise AssertionError((addr,n))
  def g(off,fmt):return struct.unpack('>'+fmt,mem(a4+off-65536,struct.calcsize('>'+fmt)))[0]
  count=g(0xaf04,'H');ptr=g(0xaf06,'I');assert 0<count<100
  world.append(dict(name='traffic',base=ptr,size=count*46,count=count,stride=46,pointer_global=0xaf06,count_global=0xaf04))
  for i in range(count):
   actor=struct.unpack('>I',mem(ptr+i*46+8,4))[0]
   world.append(dict(name='actor'+str(i),base=actor,size=44,count=1,stride=44))
  for name,po,co in [('main_objects',0x9962,0x9966),('aux_objects',0x9968,0x996c)]:
   count=g(co,'H');ptr=g(po,'I');assert 0<count<500
   world.append(dict(name=name,base=ptr,size=count*56,count=count,stride=56,pointer_global=po,count_global=co))
 for k in ['physics','controls']+(['world'] if a.world else []):(out/(k+'.bin')).write_bytes(b'')
 clock_sites=[0x7dea,0x8de0,0x938c,0x93c6,0x93d0,0x945c,0xb15c,0xb172,0x10060,0x10476,0x104ac,0x10516,0x105d8,0x105e8,0x10edc,0x1196c]
 clock_expr=[f'*(unsigned int*){a4+off-65536:#x}' for off in [0x9790,0x9798]]+[f'*(unsigned char*){a4+0x979c-65536:#x}']
 lines=[f'gdb break *{base+0x7c32:#x}',f'break *{base+0xcdb0:#x}',f'break *{base+0x3f2:#x}','set $s3n=0','set $s3f=0','set $clockn=0','set $clockok=1']+[f'break *{base+x:#x}' for x in clock_sites]
 if clock_tape:lines += ['set $clockstop=0']
 lines += [f'while $s3n < {a.steps} && $clockok'+(' && !$clockstop' if clock_tape else ''),'continue',f'if $pc == {base+0x3f2:#x}','set $s3f=$s3f+1','end',f'if $pc == {base+0x7c32:#x}']
 lines += [f'append binary memory {s.rel}/controls.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += ['end',f'if $pc == {base+0xcdb0:#x}','printf "S3STEP %d %d\\n",$s3n,$s3f']
 lines += [f'append binary memory {s.rel}/physics.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in regions]
 lines += [f'append binary memory {s.rel}/world.bin {r["base"]:#x} {r["base"]+r["size"]:#x}' for r in world]
 lines += ['set $s3n=$s3n+1','end', 'if '+ ' || '.join(f'$pc=={base+x:#x}' for x in clock_sites)]
 if clock_tape:lines += ['set $clockstop=1']
 lines += ['printf "CLOCK %u %u %u %u %u\\n",'+','.join(['$pc-'+str(base),'$s3n']+clock_expr),'set $clockn=$clockn+1','end','end']
 if not clock_tape:
  lines += ['printf "CLOCKDONE %u %u\\n",$clockok,$clockn','delete'];reply=command('\n'.join(lines))
 else:
  # GDB guest writes are ignored by this stub. Stop at each clock observation,
  # update only the two clocks/expiry through the signature-verified host helper,
  # and read them back through GDB before allowing guest execution to continue.
  init=lines[:lines.index(next(x for x in lines if x.startswith('while ')))];loop=lines[len(init):]
  command('\n'.join(init));chunks=[];writes=[];signature=(out/'game-code.bin').read_bytes()[:48].hex()
  for index,expected in enumerate(clock_tape['observations']):
   chunk=command('gdb set $clockstop=0\n'+'\n'.join(loop));chunks.append(chunk)
   rows=re.findall(r'^CLOCK (\d+) (\d+) (\d+) (\d+) (\d+)$',chunk,re.M)
   assert len(rows)==1,(index,chunk[-500:]);got=list(map(int,rows[0]))
   if got[:2]!=expected[:2]:
    (out/'events.log').write_text('\n'.join(chunks));raise AssertionError(('clock order',index,got,expected))
   addresses=','.join(hex(a4+off-65536) for off in [0x9790,0x9798])
   payload=struct.pack('>I',expected[2]).hex()+','+struct.pack('>IB',expected[3],expected[4]).hex()
   proof=command(f'poke {addresses} {payload} {signature} {base:#x}')
   assert 'VERIFIED' in proof
   readback=command('gdb maintenance flush dcache\nprintf "READBACK %u %u %u\\n",'+','.join(clock_expr))
   values=list(map(int,re.search(r'READBACK (\d+) (\d+) (\d+)',readback).groups()));assert values==expected[2:],(index,values,expected)
   writes.append(dict(index=index,site=expected[0],step=expected[1],values=values,verified=True))
   if index%250==0:print('Verified clock writes',index,flush=True)
  chunks.append(command('gdb set $clockstop=0\n'+'\n'.join(loop)+'\nprintf "CLOCKDONE %u %u\\n",$clockok,$clockn\ndelete'))
  reply='\n'.join(chunks);(out/'clock-write-verification.json').write_text(json.dumps(dict(source_sha256=clock_tape_sha,writes=writes),indent=2)+'\n')
 (out/'events.log').write_text(reply)
 observations=[list(map(int,row)) for row in re.findall(r'^CLOCK (\d+) (\d+) (\d+) (\d+) (\d+)$',reply,re.M)];(out/'clock-observations.json').write_text(json.dumps(dict(sites=clock_sites,observations=observations,replayed=bool(clock_tape)),indent=2)+'\n')
 assert 'CLOCKDONE 1 ' in reply, 'Clock read site/step sequence diverged; inspect events.log'
 events=[dict(step=int(i),field=int(f)) for i,f in re.findall(r'^S3STEP (\d+) (\d+)$',reply,re.M)];assert len(events)==a.steps
 meta=dict(s.metadata,snapshot_size=size,world_regions=world,world_snapshot_size=sum(r['size'] for r in world),events=events,input='Compiled input diagnostic; mode and coordinates depend on build flags. Input globals are retained at controls entry, before per-pass reassertion. No pose/velocity/RNG writes. Counterfactual replay writes only elapsed/remaining BCD clocks and expiry byte at the explicitly recorded main-context read sites; unmodified record run writes nothing.');(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
 for k in ['physics','controls']+(['world'] if a.world else []):
  path=out/(k+'.bin');assert path.stat().st_size%(sum(r['size'] for r in world) if k=='world' else size)==0;(out/(k+'.sha256')).write_text(sha(path)+'\n');subprocess.run(['zstd','-q','-3',str(path)],check=True);path.unlink()
 print(events[-1],flush=True)
finally:s.close()
