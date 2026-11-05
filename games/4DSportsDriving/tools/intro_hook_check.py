import json,re,struct,sys,subprocess
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'anchor.json').read_text());b=(p/'memory.bin').read_bytes()
s={n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9a-fA-F]+)\s*$',(p/'slave.lst').read_text(encoding='latin1'),re.M)}
at=m['game_base']+0x2302c-m['memory_base'];expected=b'\x4e\xb9'+struct.pack('>I',m['slave_base']+s['intro_present'])+b'\x4e\x71';assert b[at:at+8]==expected
(p/'intro-hook-check.json').write_text(json.dumps(dict(installed=True,game_offset='0x2302c',bytes=expected.hex(),slave_sha256=m['slave_sha256']),indent=2))
subprocess.run([sys.executable,'tools/p3_cache_check.py',str(p)],check=True)
for name in ['discovery.bin','live-discovery.bin']:(p/name).unlink(missing_ok=True)
print('Intro-only swap hook installed; gameplay reached')
