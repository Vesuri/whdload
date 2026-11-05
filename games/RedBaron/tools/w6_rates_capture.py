import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from rate_history import check_capture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');rate=base+symbol('time_rate_queue')
h3=m['h3'] if 'h3' in m else json.loads((a.capture/'entry-steps.json').read_text())['h3']
def dump(at,n,name):r.command(f'gdb dump binary memory {a.capture}/{name} {at:#x} {at+n:#x}')
dump(state,60,'rate-initial-clock.bin');dump(rate,268,'rate-initial-queue.bin')
def u(at):return f'*(unsigned int*){at:#x}'
def w(at):return f'*(unsigned short*){at:#x}'
args=[u(state+28),u(state+20),u(state+44),w(rate+8),w(h3+0x4838),w(state+16),w(state+26),*[u(state+o) for o in (0,4,8,12)],u(sim+0x30006)]
cmd=['delete','set $n=0',f'break *{sim+0x21d30:#x}','commands','silent','printf "RATE '+('%u '*12).strip()+'\\n", '+', '.join(args),'set $n=$n+1','if $n < 80','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'rate.log').write_text(reply)
rows=[list(map(int,x.split())) for x in re.findall(r'^RATE ([0-9 ]+)$',reply,re.M)];assert len(rows)==80,reply[-2000:]
for name,n,file in [('time_rate_queue',268,'rate-queue.bin'),('time_rate_log',768,'rate-acquisition.bin'),('time_rate_count',4,'rate-count.bin'),('time_rate_test_result',4,'rate-selftest.bin')]:dump(base+symbol(name),n,file)
result=check_capture((a.capture/'rate-initial-clock.bin').read_bytes(),(a.capture/'rate-initial-queue.bin').read_bytes(),(a.capture/'rate-queue.bin').read_bytes(),(a.capture/'rate-acquisition.bin').read_bytes(),int.from_bytes((a.capture/'rate-count.bin').read_bytes(),'big'),rows,int.from_bytes((a.capture/'rate-selftest.bin').read_bytes(),'big'))
result['sha256']=m['slave_sha256'];(a.capture/'rate-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
