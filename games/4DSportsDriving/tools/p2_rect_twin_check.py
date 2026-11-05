import json,struct,hashlib,sys
from pathlib import Path
cap=Path(sys.argv[1]);meta=json.loads((cap/'anchor.json').read_text());b=(cap/'memory.bin').read_bytes();at=b.index(b'4DRECTWN');passed,failed,active=struct.unpack_from('>IIH',b,at+8)
assert passed>=48,(passed,failed,active)
assert failed==0 and active==0,(passed,failed,active)
r={'passed_whole_plane_pairs':passed,'failed':failed,'plane_bytes':8000,'initial_pixels_identical':True,'reference':'native D-only register writes after restoring the exact initial plane','production_sha256':hashlib.sha256(Path('tmp/build/4DSportsDriving.slave').read_bytes()).hexdigest(),'diagnostic_sha256':meta['slave_sha256'],'scope':'In-process 68020 live rectangle pairs for 320x200 display planes; only the ignored diagnostic source copy has buffers and extra writes.'}
(cap/'rect-twin.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
