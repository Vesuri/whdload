#!/usr/bin/env python3
"""Account for the shipped/rebuilt slave's binary differences and check pristine inputs."""
import hashlib,json,struct
from pathlib import Path
import _amigaxdev
from amitools.binfmt.BinFmt import BinFmt
ROOT=Path(__file__).resolve().parents[1]
def code(p):return bytes(BinFmt().load_image(str(p)).get_segments()[0].get_data())
old=code(ROOT/'tmp/game/Gunship/Gunship.slave')
new=code(ROOT/'tmp/build/release/Gunship.Slave')
start_old=old.index(bytes.fromhex('d281d281'));start_new=new.index(bytes.fromhex('d281d281'))
x=bytearray(old[start_old:]);y=bytearray(new[start_new:])
# Every changed operand in the 780-byte game-specific code/patch-list tail.
# Values are SDK or string addresses after PC-relative decoding, not opaque masks.
refs={0x6:('_resload',0x12c0,0x1220),0x128:('_resload',0x12c0,0x1220),0x134:('_resload',0x12c0,0x1220),0x140:('_dosname',0x11fe,0x115e),0x150:('_assign',0x12f0,0x1238),0x156:('_dos_assign',0x618,0x62c),0x15a:('_program',0x137e,0x12ae),0x15e:('_args',0x1386,0x12b6),0x172:('_resload',0x12c0,0x1220),0x18c:('_resload',0x12c0,0x1220),0x2b2:('_flushcache',0x125c,0x11bc),0x2f4:('_resload',0x12c0,0x1220)}
for off,(name,a,b) in refs.items():
 assert start_old+off+struct.unpack_from('>h',x,off)[0]==a,(name,'shipped')
 assert start_new+off+struct.unpack_from('>h',y,off)[0]==b,(name,'rebuilt')
 x[off:off+2]=y[off:off+2]
assert x==y,'unexplained game-specific byte differences'
so=old.index(b'$VER:');sn=new.index(b'$VER:')
assert old[so:start_old].replace(b' (15-feb-2020  10:28:05)',b'')==new[sn:start_new]
checked=0
for stem,folder in [('Gunship','.'),('Gunship_v1.2_0658','.')]:
 manifest=json.loads((ROOT/f'tmp/archives/{stem}.files.json').read_text())
 for path,digest in manifest.items():
  assert hashlib.sha256((ROOT/'tmp/game'/folder/path).read_bytes()).hexdigest()==digest,path
  checked+=1
report=dict(shipped_code_bytes=len(old),rebuilt_code_bytes=len(new),sdk_prefix_bytes=dict(shipped=so,rebuilt=sn),date_bytes_removed=start_old-so-(start_new-sn),game_tail_bytes=len(x),game_tail_equal_after_symbol_relocation=True,relocated_symbols={hex(k):v for k,v in refs.items()},pristine_files_checked=checked)
(ROOT/'tmp/a1/rebuild-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
