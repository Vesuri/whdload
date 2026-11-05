import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path('tools').resolve()))
from message_time import check_capture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);p.add_argument('--resume',action='store_true');a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');msg=base+symbol('time_message_state');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3']
def dump(at,n,name):r.command(f'gdb dump binary memory {a.capture}/{name} {at:#x} {at+n:#x}')
def u(at):return f'*(unsigned int*){at:#x}'
def w(at):return f'*(unsigned short*){at:#x}'
def b(at):return f'*(unsigned char*){at:#x}'
active=f'({u(state+20)}-{u(state+44)})'
if not a.resume:dump(base+symbol('time_message_count'),4,'message-initial-count.bin')
args=[u(state+28),active,w(msg+8),w(h3+0x4820),b(h3+0x711c),u(state+36),u(msg),u(h3+0x481c)]
erase=[active,w(h3+0x4820),b(h3+0x711c),u(state+36),u(h3+0x9d6a),u(h3+0x9d66)]
cmd=['delete','set $n=0',f'break *{sim+0xab2:#x}','commands','silent','printf "ERASE '+('%u '*6).strip()+'\\n", '+', '.join(erase),'continue','end',f'break *{sim+0x21d30:#x}','commands','silent','printf "MSG '+('%u '*8).strip()+'\\n", '+', '.join(args),'set $n=$n+1','if $n < 100','continue','end','end','continue']
reply=r.command('gdb '+'\n'.join(cmd))
if a.resume:reply=(a.capture/'message.log').read_text()+reply
(a.capture/'message.log').write_text(reply)
rows=[list(map(int,x.split())) for x in re.findall(r'^MSG ([0-9 ]+)$',reply,re.M)];erasures=[list(map(int,x.split())) for x in re.findall(r'^ERASE ([0-9 ]+)$',reply,re.M)];assert len(rows)>=100,reply[-2000:]
for name,n,file in [('time_message_log',3072,'message-events.bin'),('time_message_count',4,'message-count.bin'),('time_message_test_result',4,'message-selftest.bin')]:dump(base+symbol(name),n,file)
result=check_capture((a.capture/'message-events.bin').read_bytes(),int.from_bytes((a.capture/'message-count.bin').read_bytes(),'big'),int.from_bytes((a.capture/'message-initial-count.bin').read_bytes(),'big'),rows,erasures,int.from_bytes((a.capture/'message-selftest.bin').read_bytes(),'big'),[base+symbol('time_message_fixture_'+name) for name in ('first','second','third')])
result['sha256']=m['slave_sha256'];(a.capture/'message-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
