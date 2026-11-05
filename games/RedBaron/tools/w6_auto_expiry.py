"""Controlled native expiry: override eligibility registers and prime one decrement.
No debugger RAM writes. Does not validate gameplay eligibility or physical keys.
"""
import json,re,sys
from pathlib import Path
import route_status as r
sys.path.insert(0,'tools')
from presentation_state import symbol
p=Path(sys.argv[1]);m=json.loads((p/'entry.json').read_text());lines=(p/'slave.lst').read_text(encoding='latin-1').splitlines();base=m['entry']['game_anchor']-symbol(lines,'tape_game_anchor');at=lambda n:base+symbol(lines,n);sim=m['entry']['sim'];h3=json.loads((p/'entry-steps.json').read_text())['h3']
cmd=['delete','set $decrements=0',f'break *{sim+0x21b46:#x}','commands','silent','set $d0=2','set $d5=0','set $d6=0','continue','end',f'break *{sim+0x21b74:#x}','commands','silent','if $decrements == 0','set $d0=29872','end',f'printf "DECR %u %u\\n", *(unsigned short*){h3+0x783e:#x}, $d0','set $decrements=$decrements+1','continue','end',f'break *{at("time_pause_menu"):#x}','continue',f'printf "EXPIRY %u %u %u\\n", *(unsigned short*){h3+0x783e:#x}, *(unsigned short*){h3+0x7838:#x}, *(unsigned short*){h3+0x783a:#x}','delete']
raw=r.command('gdb '+'\n'.join(cmd));(p/'expiry-entry.log').write_text(raw)
rows=[tuple(map(int,x)) for x in re.findall(r'DECR (\d+) (\d+)',raw)];assert rows==[(30000,29872),(128,128),(0,128)],rows
assert re.search(r'EXPIRY 10000 1 0',raw),raw[-1000:]
print('Native expiry/reload edge passed; paused at automatic menu wrapper',flush=True)
# Enter the native menu and supply one decoded Escape return to its keyboard API.
cmd=['set $esc_sent=0',f'break *{sim+0x309fc:#x}','commands','silent','if $esc_sent == 0','set $d0=0x45','set $esc_sent=1','end','continue','end',f'break *{at("time_auto_observe"):#x}','continue',f'printf "RETURN %u %u %u %u\\n", $d0, *(unsigned short*){at("time_auto_exit"):#x}, *(unsigned long*){at("time_auto_modal"):#x}, *(unsigned long*){at("time_loop_state")+44:#x}','delete']
raw2=r.command('gdb '+'\n'.join(cmd));(p/'expiry-return.log').write_text(raw2);print(raw2[-1200:],flush=True)
