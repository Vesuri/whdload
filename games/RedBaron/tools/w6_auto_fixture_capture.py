"""Observe compiled automatic-menu fixture; never modify target state."""
import argparse,json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=argparse.ArgumentParser();p.add_argument('capture',type=Path);a=p.parse_args();m=json.loads((a.capture/'entry.json').read_text());lines=(a.capture/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);sim=m['entry']['sim'];h3=json.loads((a.capture/'entry-steps.json').read_text())['h3'];state=at('time_loop_state')
cmd=['delete',f'break *{sim+0x21b74:#x}','commands','silent',f'printf "DECR %u %u\\n", *(unsigned short*){h3+0x783e:#x}, $d0','continue','end',f'break *{at("time_auto_observe"):#x}','commands','silent',f'printf "AUTO %u %u %u %u %u %u %u\\n", $d0, *(unsigned short*){h3+0x783e:#x}, *(unsigned short*){at("time_auto_exit"):#x}, *(unsigned long*){state+44:#x}, *(unsigned long*){state+28:#x}, *(unsigned long*){at("time_pose_header")+4:#x}, *(unsigned short*){at("time_auto_fixture_menus"):#x}','continue','end',f'break *{at("time_loop_exit"):#x}','continue',f'printf "EXIT %u %u %u %u %u\\n", $d0, $sp, $a5, *(unsigned long*){state+28:#x}, *(unsigned short*){at("time_auto_exit"):#x}','delete','si 6',f'printf "CLEARED %u %u\\n", *(unsigned long*){state+40:#x}, *(unsigned short*){at("time_keys_ready"):#x}']
raw=r.command('gdb '+'\n'.join(cmd));(a.capture/'auto-fixture.log').write_text(raw)
dec=[list(map(int,x)) for x in re.findall(r'^DECR (\d+) (\d+)$',raw,re.M)]
rows=[list(map(int,x.split())) for x in re.findall(r'^AUTO ([0-9 ]+)$',raw,re.M)]
exitrow=list(map(int,re.search(r'^EXIT ([0-9 ]+)$',raw,re.M)[1].split()))
assert dec==[[128,128],[0,128],[128,128],[0,128]],dec
assert [x[0] for x in rows]==[4,4,4,3],rows
assert [x[1] for x in rows]==[0,10000,0,10000]
assert [x[2] for x in rows]==[0,0,0,3]
assert [x[6] for x in rows]==[0,1,1,2]
assert all(x[4]==x[5] for x in rows)
assert rows[1][3]>rows[0][3] and rows[3][3]>rows[2][3]
assert exitrow[0]==1 and exitrow[1]==exitrow[2]-68 and exitrow[3]==rows[-1][4] and exitrow[4]==0,exitrow
assert re.search(r'^CLEARED 0 0$',raw,re.M),raw[-1000:]
result=dict(sha256=m['slave_sha256'],decrements=dec,rows=rows,exit=exitrow,passed=True,scope='CPU fixture: forced eligibility and synthetic menu choices. Original countdown and native result/exit paths execute; real UI and eligibility are separate gates.')
(a.capture/'auto-fixture-result.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
