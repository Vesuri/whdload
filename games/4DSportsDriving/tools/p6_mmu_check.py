import json,re,sys,subprocess,struct,zlib
from pathlib import Path
from profile_window import command,ROOT
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());a=m['data_base']+0x7ffe;sb=m['slave_base']
sym={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
def rd(expr):
 s=command('gdb p /u '+expr);return int(re.search(r'\$\d+ = (\d+)',s)[1])
def tap(k):command(f'gdb monitor key {k:x} 1\nmonitor fields 10\nmonitor key {k:x} 0\nmonitor fields 15')
cache=command('gdb monitor cacheinfo');(p/'cache-state.txt').write_text(cache)
assert rd(f'*(unsigned short*){a-0x15fa:#x}')==50
assert rd(f'*(unsigned int*){sb+sym["sim_preferences_status"]:#x}')==1
command('gdb monitor key 4c 0\nmonitor key 63 1');tap(0x24);command('gdb monitor key 63 0\nmonitor fields 100')
for _ in range(5):tap(0x4d)
tap(0x44);tap(0x45)
for _ in range(20):
 saves=rd(f'*(unsigned int*){sb+sym["sim_preferences_saves"]:#x}')
 if saves:break
 command('gdb monitor fields 50')
assert saves==1,saves
assert rd(f'*(unsigned int*){sb+sym["sim_preferences_status"]:#x}')==1
assert rd(f'*(unsigned short*){a-0xbc:#x}')==20
assert rd(f'*(unsigned short*){a-0x15fa:#x}')==50
command('shot '+str(p/'before-quit.png'))
command('gdb delete\nmonitor key 5d 1\nmonitor fields 30\nmonitor key 5d 0\nmonitor fields 400')
image=ROOT/'tmp/run/default/.run/dh1.hdf'
listing=subprocess.check_output(['xdftool',str(image),'list'],text=True);(p/'disk-list.txt').write_text(listing)
for _ in range(12):
 if 'quit-ok.txt' in listing.lower():break
 command('gdb monitor fields 300')
 listing=subprocess.check_output(['xdftool',str(image),'list'],text=True)
assert 'quit-ok.txt' in listing.lower(),listing
subprocess.run(['xdftool',str(image),'read','quit-ok.txt',str(p/'quit-ok.txt')],check=True)
assert 'P6_QUIT_OK' in (p/'quit-ok.txt').read_text()
subprocess.run(['xdftool',str(image),'read','data/4DPhysics.cfg',str(p/'4DPhysics.cfg')],check=True)
b=(p/'4DPhysics.cfg').read_bytes();assert len(b)==16 and b[:8]==b'4DPHYS50' and struct.unpack_from('>H',b,10)[0]==20 and zlib.crc32(b[:12])==struct.unpack_from('>I',b,12)[0]
for line in listing.splitlines():
 name=line.split()[0] if line.split() else ''
 if name.lower().endswith('.whdl_register'):
  subprocess.run(['xdftool',str(image),'read',name,str(p/'whdl_register.txt')],check=True)
assert (p/'whdl_register.txt').exists(),listing
text=(p/'whdl_register.txt').read_text(encoding='latin1');assert 'Return OK' in text,text
assert re.search(r'TC\s*[:=]\s*(?:0x)?0*8000\b',text,re.I),text
command('shot '+str(p/'after-quit.png'))
(p/'mmu-check.json').write_text(json.dumps(dict(cpu='68040',TC='8000',startup=True,gameplay_rate=50,preferences_loaded=50,preferences_saved=20,physical_crc=True,normal_quit=True,shell_resumed=True,slave_sha256=m['slave_sha256'],scope='Native IDE boot, MMU enabled, no NoMMU option. Functional check, not a performance result.'),indent=2))
print('MMU FUNCTIONAL PASS')
