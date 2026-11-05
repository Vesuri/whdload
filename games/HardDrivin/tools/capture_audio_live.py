import argparse,json,os,re,shutil
from capture_demo import ROOT,command
from capture_session import Session
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--profile',default='a1200-020');p.add_argument('--slave',default='s4-audio-live.slave');p.add_argument('--custom1',type=int,default=1);p.add_argument('--delay',type=int,default=0);p.add_argument('--steps',type=int,default=0);p.add_argument('--gate',action='store_true');p.add_argument('--contact',action='store_true');p.add_argument('--impact',action='store_true');p.add_argument('--gate-kind',choices=['offroad','skid','contact','landing','object'],default='offroad');p.add_argument('--fields',type=int,default=500);a=p.parse_args();a.contact=a.contact or (a.gate and a.gate_kind in ('contact','landing'));os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=f' CUSTOM1={a.custom1}'
try:
 s.boot();base=s.layout['code_base'];a4=s.layout['a4']
 if a.gate:
  hits={}
  audio_sig={'offroad':b'HDLIVEAU','skid':b'HDSKIDAU','contact':b'HDCONTAU','landing':b'HDLANDAU','object':b'HDOBJAU1'}[a.gate_kind]
  for bank,b in s.dump_banks('audio-state'):
   for sig in [audio_sig,b'HDDISP01',b'HDRPLAY1',b'HDAUDMAT']:
    i=b.find(sig)
    if i>=0:
     assert sig not in hits;hits[sig]=bank+i+8
     if sig==b'HDAUDMAT':math=b[i+8:i+8+456]
  assert all(sig in hits for sig in [audio_sig,b'HDDISP01',b'HDRPLAY1'])
  if b'HDAUDMAT' in hits:
   import struct
   inputs=[(1,100,10),(0,100,10),(0,101,11),(0,107,12),(0,108,13),(0,108,14),(0,109,16),(0,120,16),(0,120,17),(0,128,18),(1,0xfffffffc,0xfffffffe),(0,3,0xffffffff),(0,4,0),(0,4,1),(0,4,2),(0,4,4),(0,65539,5),(0,65539,5),(0,65540,6)]
   last=serial=requests=emitted=valid=0
   for i,(reset,now,step) in enumerate(inputs):
    if reset:last=serial=requests=emitted=valid=0
    gap=(step-serial)&0xffffffff;requests+=1
    due=not valid or gap>1 or (gap==1 and ((now-last)&0xffffffff)>=8)
    if due:last=now if not valid or gap>1 else (now-((now-last)&7))&0xffffffff;emitted+=1;valid=255
    serial=step
    got=struct.unpack_from('>6I',math,i*24);assert got==(int(due),last,serial,requests,emitted,valid<<24),(i,got)
   (out/'math-check.json').write_text(json.dumps(dict(passed=True,cases=19))+'\n')
 points=[0x3f2,0x8ae,0x760,0x7b6,0xcdb0,0x832]
 lines=['gdb break *'+hex(base+points[0])]+['break *'+hex(base+i) for i in points[1:]]+['set $fields=0','set $steps=0',f'while $steps<{a.steps}' if a.steps else f'while $fields<{a.fields}','continue',f'if $pc=={base+0x3f2:#x}','set $fields=$fields+1','end',f'if $pc=={base+0xcdb0:#x}','set $steps=$steps+1','end',f'if $pc=={base+0x8ae:#x}',f'printf "EVENT %u %u %u %u\\n",$fields,$steps,*(unsigned short*)($sp+4),*(unsigned int*)$sp-{base}','end',f'if $pc=={base+0x760:#x}','printf "REQUEST %u %u %u %u\\n",$fields,$steps,*(unsigned short*)($sp+4),*(unsigned short*)($sp+12)','end',f'if $pc=={base+0x7b6:#x}','printf "START %u %u %u %u\\n",$fields,$steps,*(unsigned short*)($a5+8),*(unsigned short*)($a5+16)','end',f'if $pc=={base+0x832:#x}','printf "ENGINE %u %u\\n",$fields,$steps','end','end','printf "END %u %u\\n",$fields,$steps','delete']
 if a.gate:
  au=hits[audio_sig];entry={'offroad':0xb162,'skid':0xb620,'contact':0xcd4e,'landing':0xcc80,'object':0xbcfe}[a.gate_kind];leave=entry+10;ds=hits[b'HDDISP01'];rp=hits[b'HDRPLAY1']
  lines.insert(1,f'break *{base+entry:#x}');lines.insert(1,f'break *{base+leave:#x}')
  at=lines.index('continue')+1
  for tag,off in [('BEFORE',entry),('AFTER',leave)]:
   expressions=[f'*(unsigned int*){x:#x}' for x in [rp,ds+8,au,au+4,au+8,au+12]]+[f'*(unsigned char*){x:#x}' for x in [au+16,ds+24]]
   if a.gate_kind=='object':expressions += ['$a3',f'*(unsigned int*){au+20:#x}',f'(*(unsigned short*){a4-0x66e2:#x}|*(unsigned short*){a4-0x66e0:#x}|*(unsigned short*){a4-0x66de:#x})']
   lines[at:at]=[f'if $pc=={base+off:#x}','printf "'+tag+' '+' '.join(['%u']*len(expressions))+'\\n",'+','.join(expressions),'end']
 if a.contact:
  contacts=[0xcb0a,0xbc14,0xbcfe,0xbdde,0xcc80,0xcd4e]
  for off in contacts:lines.insert(1,f'break *{base+off:#x}')
  at=lines.index('continue')+1
  for off in contacts:
   expr=[str(off),'$fields','$steps',f'*(unsigned char*){a4-0x66f0:#x}',f'*(short*){a4-0x66f2:#x}',f'*(short*){a4-0x66d8:#x}']
   expr += [f'*(short*){a4+x-65536:#x}' for x in [0x947e,0x9480,0x9482,0x9484]]
   expr += ['$a3' if off in [0xbc14,0xbcfe,0xbdde] else '0']
   lines[at:at]=[f'if $pc=={base+off:#x}','printf "CONTACT '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 if a.impact:
  # Before the collision impulse, then immediately before each object sound.
  sites=[0xbc14,0xbc62,0xbcfe,0xbd40,0xbdde,0xbcf2,0xbdd2]
  for off in sites:lines.insert(1,f'break *{base+off:#x}')
  at=lines.index('continue')+1
  for off in sites:
   expr=[str(off),'$fields','$steps','$a3']
   expr += [f'*(short*){a4+x-65536:#x}' for x in [0x9928,0x992c,0x991e,0x9920,0x9922,0x9908,0x990a,0x990c]]
   expr += [f'*(int*){a4+x-65536:#x}' for x in [0x98fc,0x9900,0x9904]]
   expr += ['*(unsigned char*)($a3+25)','*(unsigned char*)($a3+32)']
   lines[at:at]=[f'if $pc=={base+off:#x}','printf "IMPACT '+' '.join(['%d']*len(expr))+'\\n",'+','.join(expr),'end']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply)
 from analyse_audio_capture import analyse
 analyse(out,reply,a)
finally:s.close()
