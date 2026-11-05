from pathlib import Path
import gzip,subprocess,sys,hashlib,json
r=Path(__file__).resolve().parents[1];p=r/'tmp/step5/c4-q03-render-profile-a1200-fast-h3-candidate';raw=gzip.decompress((p/'detail.bin.gz').read_bytes());(p/'detail.bin').write_bytes(raw)
for name in ['waits','calls']:
 source=(r/f'tools/analyze_render_{name}.py').read_text().replace("Path('tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-rc2-trace')",'Path(sys.argv[1])');script=r/f'tools/analyze_h3_{name}.py';script.write_text(source)
 with (r/f'tmp/h3-{name}.log').open('w') as f:subprocess.run([sys.executable,str(script),str(p)],stdout=f,stderr=subprocess.STDOUT,check=True)
assert hashlib.sha256((p/'detail.bin').read_bytes()).digest()==hashlib.sha256(raw).digest();(p/'detail.bin').unlink();print('Current H3 wait and call analyses saved; verified compressed trace retained')
