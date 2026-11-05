"""Prove placement of every P3 game callback and execution of copied renderer."""
import json,re,sys,os,subprocess
from pathlib import Path
from profile_window import command
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());syms={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]+)$',(p/'slave.lst').read_text(encoding='latin1'),re.M)};base=m['slave_base'];g=m['game_base']
s=command(f'gdb p /x *(unsigned int*){base+syms["p3_clone_address"]:#x}')
clone=int(re.search(r'\$\d+ = 0x([0-9a-f]+)',s)[1],16);n=syms['p3_clone_end']-syms['slv_base']
bank=os.environ['P3_CODE_BANK'];assert (0<clone<0x200000) if bank=='chip' else (0x200000<=clone<0xc00000)
# All game entries installed by pl_raster (pipeline intentionally off in both).
hooks={0x21228:'raster_bg_enter',0x21ba8:'raster_bg_exit',0x347b0:'raster_bg_rect',0x32242:'raster_bg_bitmap',0x323a6:'raster_bg_bitmap_end',0xab86:'raster_draw_enter',0xaed0:'raster_draw_exit',0x3980e:'raster_own_blitter',0x39800:'perf_disown_blitter',0x2c6d6:'raster_solid',0x2bf5c:'raster_two',0x2cd44:'raster_solid_end',0x2c632:'raster_two_end',0x2cdca:'raster_degenerate',0x339c4:'raster_line_hook',0x33aa8:'raster_line_end'}
reads=[f'p /x *(unsigned int*){g+off+2:#x}' for off in hooks]
s=command('gdb '+'\n'.join(reads));values=[int(x,16) for x in re.findall(r'\$\d+ = 0x([0-9a-f]+)',s)]
assert len(values)==len(hooks),s
for (off,name),ptr in zip(hooks.items(),values):assert ptr==clone+syms[name],(hex(off),name,hex(ptr),hex(clone+syms[name]))
entry=clone+syms['raster_solid_fast']
s=command(f'gdb delete\ntbreak *{entry:#x}\ncontinue\ninfo registers pc\ndelete');(p/'full-code-execution.log').write_text(s)
assert re.search(r'pc\s+0x'+format(entry,'x')+r'\b',s),s
names=('raster_buffer','raster_staged_count','raster_fallback_count')
s=command('gdb '+'\n'.join(f'p /u *(unsigned int*){clone+syms[name]:#x}' for name in names));v=[int(x) for x in re.findall(r'^\$\d+ = (\d+)',s,re.M)];assert len(v)==3,s
buffer,staged,fallback=v;assert 0x200000<=buffer<0xc00000 and 0x200000<=g<0xc00000 and staged>10
# Verify the copied instructions at every patched callback and the solid kernel.
for name in list(hooks.values())+['raster_solid_fast']:
 orig=p/(name+'-original.bin');copy=p/(name+'-copy.bin');a=base+syms[name];b=clone+syms[name]
 command(f'gdb dump binary memory {orig.relative_to(Path.cwd())} {a:#x} {a+16:#x}\ndump binary memory {copy.relative_to(Path.cwd())} {b:#x} {b+16:#x}')
 assert orig.read_bytes()==copy.read_bytes(),name
r=dict(bank=bank,clone_address=hex(clone),copied_prefix_bytes=n,all_renderer_hooks_in_clone=True,renderer_hooks=len(hooks),executed=True,entry_instructions_match=True,slave_base=hex(base),game_base=hex(g),staging_base=hex(buffer),staged=staged,fallback=fallback,scope='Complete P3 rasterizer and its local state/ownership helpers copied; geometry and simulation stay in original Fast-RAM code. Both variants use identical copy/flush/trampoline and original early display wait.')
(p/'full-code-placement.json').write_text(json.dumps(r,indent=2)+'\n');print(r)
subprocess.run([sys.executable,str(Path(__file__).with_name('p3_cache_check.py')),str(p)],check=True)
