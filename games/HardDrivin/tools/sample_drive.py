import sys,json,struct
from pathlib import Path
from capture_demo import ROOT,command
name=sys.argv[1];n=int(sys.argv[2]);out=ROOT/'tmp/prof'/name;out.mkdir(exist_ok=True);rel=out.relative_to(ROOT)
# Fixed A500 calibration layout. Confirmed via code-start publication each boot.
script=f'''gdb break *0xcfb5a8
set $hd_n=0
while $hd_n < {n}
continue
set $hd_n=$hd_n+1
end
delete
'''
command(script)
print(command('gdb x/10hx 0xd7dd26'))
command(f'gdb dump binary memory {rel}/state.bin 0xd0ee16 0xd16016')
print(command(f'shot {out}/view.png'))
b=(out/'state.bin').read_bytes()
def val(o,fmt):return struct.unpack_from('>'+fmt,b,o+0x7100)[0]
print(json.dumps(dict(pose=[val(x,'h') for x in [-0x670a,-0x6708,-0x6706]],heading=val(-0x66b6,'h'),speed=val(-0x66d4,'h'),gear=val(-0x66ca,'h'),throttle=val(-0x66e4,'B'),crash=val(-0x69fa,'B'),replay=val(-0x5229,'B'),automatic=val(-0x66c2,'B'),phase_flags=[val(x,'B') for x in [-0x69fc,-0x522c]]),indent=2))
