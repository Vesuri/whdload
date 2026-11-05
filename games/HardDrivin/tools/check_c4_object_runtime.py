"""Replay recorded zero-contact terrain inputs against optimized and native code."""
from pathlib import Path
import ctypes as C,json,os,random,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0x9b0000,7));ok(u.uc_mem_map(h,0x7800000,0x800000,7))
sys.path.insert(0,'tools')
from game_image import hunks
from machine_profiles import banks
root=Path('tmp/prof/c4-jump-bad-plane');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];stop=0x41000;sp=0x4f000
images=[(addr,(root/f'loss-{name}.bin').read_bytes()) for name,addr,size in banks(meta['configuration'])]
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
def invoke(addr,arg=None):
 reg(8,sp);pack(sp,'I',stop)
 if arg is not None:pack(sp+4,'h',arg)
 ok(u.uc_emu_start(h,addr,stop,1000000,1000000));assert reg(18)==stop and reg(8)==sp+4
import subprocess
stem=Path('tmp/c4-object-runtime-check')
text=' org $42000\n'+Path('tools/c4_object_contact.s').read_text()+Path('tools/c4_support_face.s').read_text()+f'\n_phase_steering_body: dc.l ${code+0xb398:x}\n'
stem.with_suffix('.s').write_text(text);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL)
for addr,body in images:write(addr,body)
write(0x42000,stem.with_suffix('.bin').read_bytes());ok(u.uc_ctl(h,0x4000000a));reg(17,0x2000);reg(5,a4)
protected=[(a4+0xe936-65536,16),(a4+0x9944-65536,6),(a4+0xe94e-65536,18),(117524,56)]
before=[read(a,n) for a,n in protected];registers=[reg(k) for k in range(1,17)]
invoke(0x42000)
after=[read(a,n) for a,n in protected];wheels=struct.unpack('>4h',read(a4+0x947e-65536,8))
assert before==after,'Changed protected native state'
assert [reg(k) for k in range(1,8)]+[reg(k) for k in range(9,17)]==registers[:7]+registers[8:]
assert wheels==(193,193,182,3),wheels
report=dict(passed=True,wheels=wheels,protected_state_restored=True,registers_preserved=True,scope='Full assembled private object ground/world scan at saved failing jump pose, all active main-pool candidates, expected finite per-wheel result. Not runtime/trajectory acceptance.')
Path('tmp/c4-object-runtime-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
