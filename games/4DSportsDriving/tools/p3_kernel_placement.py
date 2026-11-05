import json,re,sys,os,subprocess
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['slave_base']
s=command('gdb '+'\n'.join(f'p /x *(unsigned int*){base+syms[n]:#x}' for n in ('raster_buffer','raster_code_copy')));buffer,code=[int(x,16) for x in re.findall(r'\$\d+ = 0x([0-9a-f]+)',s)]
n=syms['raster_solid_fast_end']-syms['raster_solid_fast']
script=['delete',f'dump binary memory {(p/"kernel-copy.bin").relative_to(Path.cwd())} {code:#x} {code+n:#x}',f'dump binary memory {(p/"kernel-original.bin").relative_to(Path.cwd())} {base+syms["raster_solid_fast"]:#x} {base+syms["raster_solid_fast"]+n:#x}',f'tbreak *{code:#x}','continue','info registers pc','delete']
text=command('gdb '+'\n'.join(script));(p/'kernel-execution.log').write_text(text)
assert re.search(r'pc\s+0x'+format(code,'x')+r'\b',text),text
assert (p/'kernel-copy.bin').read_bytes()==(p/'kernel-original.bin').read_bytes()
bank=os.environ['P3_CODE_BANK'];assert (code<0x200000) if bank=='chip' else (0x200000<=code<0xc00000)
assert 0x200000<=buffer<0xc00000 and 0x200000<=m['game_base']<0xc00000
r=dict(bank=bank,kernel_address=hex(code),kernel_bytes=n,executed=True,copy_matches=True,slave_base=hex(base),game_base=hex(m['game_base']),staging_base=hex(buffer),scope='Only the self-contained solid-span kernel and colour writers change placement. Game, staging, other renderer code and state stay in Fast RAM; both variants use the same allocation/copy/flush/trampoline.')
(p/'kernel-placement.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_matrix_check.py')),str(p)],check=True)
