"""Speed-triggered brake input; inspect native car state without injecting dynamics."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a500');p.add_argument('--slave',default='s4-speed-brake.slave');p.add_argument('--custom1',type=int,default=1);p.add_argument('--delay',type=int,default=0);p.add_argument('--projection',action='store_true');p.add_argument('--observe-only',action='store_true');p.add_argument('--inner-only',action='store_true');p.add_argument('--fields',type=int,default=1200);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4'];hits={}
 if not a.observe_only:
  initial=(out/'game-data.bin').read_bytes()
  gear=struct.unpack_from('>h',initial,0x7ffe-0x66ca)[0];automatic=initial[0x7ffe-0x66c2]
  (out/'initial-mode.json').write_text(json.dumps(dict(gear=gear,automatic=automatic,valid=(gear,automatic)==(1,1)),indent=2)+'\n')
  assert (gear,automatic)==(1,1), 'Braking fixture did not start in automatic first gear'
 for bank,b in s.dump_banks('brake-state'):
  for sig in [b'HDBRAKE1',b'HDSCAL01',b'HDDISP01']+([b'HDVPROJ1',b'HDPOSST1',b'HDDRIVE1',b'HDDTICK1',b'HDFIXPT1',b'HDFRAC01'] if a.projection else []):
   i=b.find(sig)
   if i>=0:
    assert sig not in hits;hits[sig]=bank+i+8
    if sig==b'HDDTICK1':tick_sites=tuple(bank+i+8+x for x in struct.unpack_from('>ii',b,i+8))
 assert all(k in hits for k in ([b'HDBRAKE1'] if not a.observe_only else [])+[b'HDSCAL01',b'HDDISP01']+([b'HDVPROJ1',b'HDPOSST1'] if a.projection else []))
 latch=hits.get(b'HDBRAKE1');sf=hits[b'HDSCAL01']-10;ds=hits[b'HDDISP01']
 def mem(addr,t='short'):return f'*({t}*){addr:#x}'
 def g(off,t='short'):return mem(a4+off-65536,t)
 latch_expr=mem(latch) if latch is not None else '0'
 cols=['field','x8','y8','z8','velocity','fall_velocity','heading','throttle','buttons','braking','mask','road','latched','interval','consumed']
 expr=['$f']+[g(i,'int') for i in [0x98fc,0x9900,0x9904]]+[g(0x9928),g(0x990e),g(0x994a),g(0x991c,'unsigned char'),g(0x95f6,'unsigned short'),g(0x9911,'unsigned char'),g(0x9910,'unsigned char'),g(0xe94a,'unsigned char'),latch_expr,mem(sf,'unsigned short') if a.custom1 else '8',mem(ds+4,'unsigned int') if a.custom1 else '0']
 lines=[f'gdb break *{base+0x3f2:#x}',f'break *{base+0xb662:#x}',f'break *{base+0xcdb0:#x}','set $f=0','set $stopped=0',f'while $f<{a.fields} && $stopped<2','continue',f'if $pc=={base+0x3f2:#x}','set $f=$f+1','end']
 for tag,off in [('BEFORE',0xb662),('AFTER',0xcdb0)]:
  lines += [f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 lines += [f'if $pc=={base+0xcdb0:#x} && {latch_expr}!=0 && {g(0x9928)}==0','set $stopped=$stopped+1','end','end','delete']
 if a.projection:
  lines.insert(lines.index('set $stopped=0'),'set $position_pending=0')
  wi=next(i for i,x in enumerate(lines) if x.startswith('while '))
  lines[wi]=f'while ($f<{a.fields} || $position_pending!=0) && $stopped<2'
  vs=hits[b'HDVPROJ1'];ps=hits[b'HDPOSST1'];ss=hits[b'HDSCAL01']
  sites=[('PIN',base+0xb578,''),('POUT',base+0xb596,'')]
  if b'HDDTICK1' in hits:
   assert b'HDDRIVE1' in hits
   guard=' && '+mem(hits[b'HDDRIVE1']+6)+'!=2'
   sites=[(tag,addr,guard) for tag,addr,_ in sites]+[('PIN',tick_sites[0],''),('POUT',tick_sites[1],'')]
  if a.inner_only:
   assert b'HDDTICK1' in hits
   sites=[('PIN',tick_sites[0],''),('POUT',tick_sites[1],'')]
  for _,addr,_ in sites:lines.insert(1,f'break *{addr:#x}')
  at=lines.index('continue')+1
  for tag,addr,guard in sites:
   lines[at:at]=[f'if $pc=={addr:#x}{guard}', 'printf "MODE '+tag+' %d %d %d %d\\n",$f,'+g(0xaf31,'unsigned char')+','+g(0x9910,'unsigned char')+','+g(0x990e),'end']
   # X axis is longitudinal on the native straight (heading360).
   expr=['$f',g(0x98fc,'int'),g(0x991e),mem(ps),mem(ps+8,'int'),mem(vs,'int'),mem(vs+12,'int'),mem(vs+24,'int'),mem(sf,'unsigned short'),mem(ss),g(0x9928)]+[g(x) for x in [0x9448,0x944a,0x944c,0x944e]]
   lines[at:at]=[f'if $pc=={addr:#x}{guard}',f'set $position_pending={1 if tag=="PIN" else 0}','printf "'+tag+' '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
   for axis in [1,2]:
    axis_expr=['$f',g(0x98fc+4*axis,'int'),g(0x991e+2*axis),mem(ps+2*axis),mem(ps+8+4*axis,'int'),mem(vs+4*axis,'int'),mem(vs+12+4*axis,'int'),mem(vs+24+4*axis,'int'),mem(sf,'unsigned short')]
    axis_tag=('Y' if axis==1 else 'Z')+tag
    lines[at:at]=[f'if $pc=={addr:#x}{guard}','printf "'+axis_tag+' '+' '.join(['%d']*len(axis_expr))+'\\n",'+','.join(axis_expr),'end']
   if tag=='PIN' and b'HDFIXPT1' in hits and addr==tick_sites[0]:
    fx=hits[b'HDFIXPT1']+8
    observed=[mem(ss+i,'int') for i in [0,4,8,12]]+[g(0x9926,'int'),g(0x992a,'int'),g(0x9936),g(0x991c,'unsigned short')]
    saved=[mem(fx+i,'int') for i in [0,4,8,12,16,20]]+[mem(fx+24),mem(fx+26,'unsigned short')]
    check=['$f',mem(sf,'unsigned short')]+observed+saved
    fixed_guard=''
    if b'HDFRAC01' in hits:
     fr=hits[b'HDFRAC01'];fixed_guard=' && '+mem(fr+10)+'==0'
     fraction=['$f',mem(sf,'unsigned short'),mem(fr+8)]+observed+saved
     lines[at:at]=[f'if $pc=={addr:#x}{guard} && {mem(fr+10)}>0', 'printf "FRAC '+' '.join(['%d']*len(fraction))+'\\n",'+','.join(fraction),'end']
    lines[at:at]=[f'if $pc=={addr:#x}{guard} && {mem(sf,"unsigned short")}>1{fixed_guard}', 'printf "FIXED '+' '.join(['%d']*len(check))+'\\n",'+','.join(check),'end']

 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 if a.observe_only:
  (out/'observation.json').write_text(json.dumps(dict(profile=a.profile,fields=a.fields,mode='read-only position operands; no braking assertion'),indent=2)+'\n');print(a.name,'captured',a.fields,'fields')
 else:
  from analyse_brake_distance import analyse
  analyse(out,reply,a)
finally:s.close()
