import json,re,subprocess,sys
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['slave_base']
s=command(f'gdb p /x *(unsigned int*){base+syms["raster_buffer"]:#x}');buffer=int(re.search(r'\$\d+ = 0x([0-9a-f]+)',s)[1],16)
r=dict(slave_base=hex(base),game_base=hex(m['game_base']),staging_base=hex(buffer));(p/'code-placement.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
assert base<0x200000,'WHDLoad ignored HUNKF_CHIP; this is not a Chip-code comparison'
assert 0x200000<=m['game_base']<0xc00000 and 0x200000<=buffer<0xc00000
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_matrix_check.py')),str(p)],check=True)
