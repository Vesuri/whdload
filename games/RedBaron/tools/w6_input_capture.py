import argparse,json,re,struct,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from input_events import check_fixture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for next_line in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',next_line)
    if match:return int(match[1],16)
 raise ValueError(name)
from runtime_buffers import live_address
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim']
cmd=['delete']
for kind,off in [('PRE',0x308b6),('POST',0x308bc)]:
 cmd += [f'break *{sim+off:#x}','commands','silent',f'printf "HOOK {kind}\\n"','info registers','continue','end']
cmd += [f'break *{m["entry"]["game_anchor"]:#x}','ignore $bpnum 9','continue','delete']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'irq-registers.log').write_text(reply)
for name,size,dest in [('time_input_observe_queue',4112,'input-queue.bin'),('time_input_fixture_log',32,'input-acquisition.bin')]:
 addr=live_address(lines,base,name,r.command)
 r.command(f'gdb dump binary memory {a.capture}/{dest} {addr:#x} {addr+size:#x}')
result=check_fixture((a.capture/'input-queue.bin').read_bytes(),(a.capture/'input-acquisition.bin').read_bytes())
blocks=re.split(r'HOOK (PRE|POST)\n',reply)
records=[]
for i in range(1,len(blocks),2):
 regs={k:int(v,16) for k,v in re.findall(r'^(\w+)\s+0x([0-9a-f]+)',blocks[i+1],re.M)}
 records.append((blocks[i],regs))
assert len(records)==8,records
for i in range(0,8,2):
 kind,before=records[i];afterkind,after=records[i+1]
 assert (kind,afterkind)==('PRE','POST')
 assert len(before)>=18 and before.keys()==after.keys(),(before,after)
 assert all(before[k]==after[k] for k in before if k not in ('pc','a0')),(before,after)
 assert after['a0']==sim+0x30f8c
 assert after['pc']==before['pc']+6
result['register_pairs_verified']=4
result['slave_sha256']=m['slave_sha256']
(a.capture/'input-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
