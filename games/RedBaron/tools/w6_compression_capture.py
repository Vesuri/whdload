import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,str(Path("tools").resolve()))
from compression_clock import check_capture
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args()
m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(errors='replace').splitlines()
def symbol(name):
 for i,line in enumerate(lines):
  if re.search(r'\b'+re.escape(name)+r':',line):
   for following in lines[i:]:
    match=re.match(r'00:([0-9A-F]+)\s',following)
    if match:return int(match[1],16)
 raise ValueError(name)
base=m['entry']['game_anchor']-symbol('tape_game_anchor');sim=m['entry']['sim'];state=base+symbol('time_loop_state');h3=json.loads((a.capture/'entry-steps.json').read_text())['h3']
def u(at):return f'*(unsigned int*){at:#x}'
def w(at):return f'*(unsigned short*){at:#x}'
phase=[u(state+i) for i in (0,4,8,12)]+[w(state+16)]
head=[u(state+20),'$f','$flag','$mult']
def log(tag,args):return 'printf "'+tag+' '+('%u '*len(args)).strip()+'\\n", '+', '.join(args)
cmd=['delete','set $n=0',f'set $origin={u(state+28)}',f'break *{base+symbol("time_core_advance"):#x}', 'commands','silent','set $f=$d0 & 65535','set $mult=$d1 & 65535',f'set $flag={w(h3+0x45a6)}',log('PRE',head+phase+[w(state+24),'0']),'continue','end',f'break *{base+symbol("time_camera_advance"):#x}','commands','silent',log('POST',head+phase+[w(state+24),'($d1 & 65535)']),'set $n=$n+1','if $n < 160','continue','end','end',f'break *{base+symbol("time_compress_clock"):#x}','commands','silent',log('CLOCKPRE',[w(h3+0x4834),w(h3+0x4836),w(h3+0x45a6)]),'continue','end',f'break *{sim+0xee0:#x}','commands','silent',log('CLOCKPOST',[w(h3+0x4834),w(h3+0x4836),w(h3+0x45a6)]),'continue','end',f'break *{sim+0x21db6:#x}','commands','silent',log('SELECTOR',['*(unsigned short*)($a5-48)',w(h3+0x45a6)]),'continue','end','continue']
reply=r.command('gdb '+'\n'.join(cmd));(a.capture/'compression.log').write_text(reply)
def rows(tag):return [list(map(int,x.split())) for x in re.findall(r'^'+tag+r' ([0-9 ]+)$',reply,re.M)]
result=check_capture(rows('PRE'),rows('POST'))
assert rows('CLOCKPRE')==rows('CLOCKPOST')
assert len(rows('CLOCKPRE'))>=30 and any(x[2] for x in rows('CLOCKPRE'))
assert all(x[0]==225 for x in rows('CLOCKPRE'))
assert all(x[0]==0 for x in rows('SELECTOR')) and any(x[1] for x in rows('SELECTOR'))
result.update(sha256=m['slave_sha256'],clock_pairs=len(rows('CLOCKPRE')),selector_rows=len(rows('SELECTOR')),fixture='CUSTOM5 bit 28 forces native compression flag after dispatcher for fixture-relative world ticks 5..34; no native eligibility or player-input claim.')
(a.capture/'compression-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
