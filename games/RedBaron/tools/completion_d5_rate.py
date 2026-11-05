"""D5 external rate/cadence window on the uninstrumented developer runtime."""
import argparse,json,re,struct
from pathlib import Path
import route_status as r
p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--fields',type=int,default=2000);a=p.parse_args()
m=json.loads((a.out/'sim.json').read_text());sim=m['sim']
listing=(a.out/'slave.lst').read_text(encoding='latin1')
syms={m[1]:int(m[2],16) for line in listing.splitlines() if (m:=re.match(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',line))}
def words(at,n):
 raw=r.command(f'gdb x/{n}wx {at:#x}');v=[]
 for line in raw.splitlines():
  if re.match(r'^0x[0-9a-f]+:',line):v += [int(x,16) for x in re.findall(r'0x[0-9a-f]+',line.split(':',1)[1])]
 assert len(v)==n,raw
 return v
r.command('stop')
# Six-byte absolute JSR installed at the loop gate, and unchanged h3 operand.
raw=r.command(f'gdb x/3hx {sim+0x21d28:#x}')
v=[int(x,16) for x in re.findall(r'0x[0-9a-f]+',raw.split(':',1)[1])];assert v[0]==0x4eb9
base=((v[1]<<16)|v[2])-syms['time_loop_gate'];state=base+syms['time_loop_state'];h3=words(base+syms['time_loop_h3'],1)[0]
(a.out/'runtime.json').write_text(json.dumps(dict(sim=sim,slave=base,h3=h3)))
quantum=int(r.command(f'gdb p/u *(unsigned short*){base+syms["time_loop_quantum"]:#x}').split('=')[1])
time_scale=int(r.command(f'gdb p/u *(unsigned short*){h3+0x3d56:#x}').split('=')[1])
scenario=a.out/'scenario.json'
if scenario.exists():assert time_scale==json.loads(scenario.read_text())['requested_time_scale'],time_scale
# A completed-world boundary excludes a partially running update.
r.command(f'until {base+syms["time_loop_gate"]:#x}')
cmd=['delete','set $field=0','set $drop=0','set $pub=0']
ledger=f'*(unsigned int*){sim+0x30006:#x}, *(unsigned int*){state+28:#x}, *(unsigned short*){h3+0x4838:#x}'
cmd += [f'printf "BEGIN %u %u %u\\n", {ledger}']
cmd += [f'break *{base+syms["time_loop_gate"]:#x}','commands','silent',f'printf "WORLD %u %u %u %u\\n", $field, {ledger}','continue','end']
# Count actual dropped updates at the original runtime CLR, without guest writes.
section=listing[listing.index(': time_debt_bound:'):]
match=re.search(r'^00:([0-9A-F]+)\s+\w+\s+\d+:\s+clr.w TIME_LOOP_DUE\(a0\)',section,re.M);assert match
cmd += [f'break *{base+int(match[1],16):#x}','commands','silent','set $drop=$drop+*(unsigned short*)($a0+24)','continue','end']
cmd += [f'break *{sim+0x3154a:#x}','commands','silent','set $pub=$pub+1','printf "PUB %u %u\\n", $field, *(unsigned int*)0xdff004','continue','end']
cmd += [f'break *{sim+0x21f4a:#x}','commands','silent','printf "FLIGHT_EXIT %u\\n", $field','end']
cmd += [f'break *{sim+0x2d34e:#x}','commands','silent','set $field=$field+1',f'if $field < {a.fields}','continue','end','end','continue',f'printf "END %u %u %u %u %u %u\\n", $field, $drop, $pub, {ledger}','delete']
raw=r.command('gdb '+'\n'.join(cmd));(a.out/'rate.log').write_text(raw)
assert 'FLIGHT_EXIT' not in raw, 'Mission ended'
start=re.search(r'BEGIN (\d+) (\d+) (\d+)',raw);end=re.search(r'END (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',raw);assert start and end,raw
cia0,step0,F0=map(int,start.groups());fields,drop,pub,cia1,step1,F1=map(int,end.groups());assert fields==a.fields and F0==F1
result=dict(quantum=quantum,time_scale=time_scale,F=F0,fields=fields,publications=pub,fps=pub*49.92041/fields,world_steps=step1-step0,cia_ticks=cia1-cia0,world_rate=(step1-step0)*quantum*F0/((cia1-cia0)*1024),dropped_steps=drop,dropped_units=drop*quantum,scope='Uninstrumented developer runtime; complete-window wall CIA and completed steps, endpoint quantization retained')
(a.out/'rate.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)
