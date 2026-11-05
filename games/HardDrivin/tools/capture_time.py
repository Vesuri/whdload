"""Read-only elapsed-time diagnostic capture; no debugger state writes."""
import argparse,json,os,re,shutil,struct
from capture_demo import ROOT,command
from capture_session import Session
from check_disabled import check
p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('name');p.add_argument('--fields',type=int,default=10000);p.add_argument('--slave',default='s4-time.slave');p.add_argument('--off',action='store_true');p.add_argument('--passes',type=int,default=120);p.add_argument('--delay',type=int,default=0);a=p.parse_args();os.chdir(ROOT)
out=ROOT/'tmp/prof'/a.name;out.mkdir(exist_ok=False);shutil.copyfile(ROOT/'tmp/build'/a.slave,out/'slave.slave');s=Session(out,a.profile,out/'slave.slave',0x10ed4,a.delay);s.env['WHD_ARGS']+=' CUSTOM1='+('0' if a.off else '1')
try:
 s.boot();base=s.layout['code_base'];hits=[]
 for bank,b in s.dump_banks('timing'):
  pos=b.find(b'HDTIME01')
  if pos>=0:hits.append(bank+pos+8)
 assert len(hits)==1,hits
 state=hits[0];s.metadata['time_state']=state
 enabled=['VERIFY_DRIVE']+(['VERIFY_SLOW'] if a.delay else [])+([] if a.off else ['CUSTOM1'])
 check_result=check(out,enabled);assert check_result['passed'],check_result
 (out/'timing.bin').write_bytes(b'')
 lines=[f'gdb break *{base+0x10edc:#x}',f'break *{base+0x3f2:#x}','set $n=0','set $f=0',f'while $n < {a.passes} && $f < {a.fields}','continue',f'if $pc == {base+0x3f2:#x}','set $f=$f+1','end',f'if $pc == {base+0x10edc:#x}',f'append binary memory {s.rel}/timing.bin {state:#x} {state+32:#x}','printf "TIME %d %d\\n",$n,$f','set $n=$n+1','end','end','delete']
 reply=command('\n'.join(lines));(out/'events.log').write_text(reply);events=[dict(index=int(i),field=int(f)) for i,f in re.findall(r'^TIME (\d+) (\d+)$',reply,re.M)];raw=(out/'timing.bin').read_bytes();assert len(raw)==32*len(events)
 for n,e in enumerate(events):
  v=struct.unpack_from('>7I4B',raw,n*32);e.update(dict(zip(['active_fields','previous','elapsed','observed','passes','T','return','active','suspended','reserved0','reserved1'],v)))
 (out/'metadata.json').write_text(json.dumps(s.metadata,indent=2)+'\n');(out/'timing.json').write_text(json.dumps(dict(events=events,ranges=check_result),indent=2)+'\n')
 if a.off:assert raw==bytes(len(raw))
 else:
  assert len(events)==a.passes or events[-1]['field']<=a.fields
  for i,e in enumerate(events):
   assert e['observed']==e['previous'] and e['passes']==i+1
   assert e['T']==min(e['elapsed'],8)*8192
   assert e['elapsed']==(e['previous']-events[i-1]['previous'] if i else 0)
 print(a.name,events[-1],flush=True)
finally:s.close()
