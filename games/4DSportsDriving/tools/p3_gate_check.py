import json,re,sys,os,subprocess
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());base=m['slave_base'];g=m['game_base'];syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
names=('raster_buffer','perf_attnflags','_custom2');s=command('gdb '+'\n'.join(f'p /u *(unsigned int*){base+syms[n]:#x}' for n in names));v=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',s,re.M)];assert len(v)==3,s
buffer,attn,custom=v
command(f'gdb dump binary memory {(p/"gate-hook.bin").relative_to(Path.cwd())} {g+0x2c6d6:#x} {g+0x2c6dc:#x}')
b=(p/'gate-hook.bin').read_bytes();expected=os.environ.get('P3_GATE_EXPECT','on')
if expected=='off':
 assert buffer==0,(buffer,attn,custom)
 original=Path('tmp/game/4DSportsDriving_v1.2_1461/4DSportsDriving/data/stunts').read_bytes()
 assert b==original[0x28+0x2c6d6:0x28+0x2c6dc],b.hex()
else:
 assert attn&2 and 0x200000<=buffer<0xc00000 and 0x200000<=g<0xc00000
 assert b==bytes.fromhex('4ef9')+(base+syms['raster_solid']).to_bytes(4,'big'),b.hex()
r=dict(expect=expected,buffer=hex(buffer),attnflags=hex(attn),custom2=custom,game_base=hex(g),hook=b.hex(),passed=True)
(p/'gate-check.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
if expected=='off':subprocess.run([sys.executable,str(Path(__file__).with_name('p3_gate_ranges.py')),str(p)],check=True)
if expected=='on':subprocess.run([sys.executable,str(Path(__file__).with_name('p3_stage_check.py')),str(p)],check=True)
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_cache_check.py')),str(p)],check=True)
