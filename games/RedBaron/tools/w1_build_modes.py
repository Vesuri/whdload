"""Isolated final builds; no runtime files are replaced."""
import hashlib,json,subprocess,sys
from pathlib import Path
import _amigaxdev  # noqa: F401 (finds amigaxdev)
from amigaxdev.env import path
root=Path(__file__).resolve().parents[1];whd=Path(path('WHDLOAD'));out=Path(sys.argv[1]).resolve();out.mkdir(exist_ok=True,parents=True);rows={}
for mode,defs in [('normal',[]),('developer',['-DDEVELOPER=1']),('verify',['-DVERIFY=1'])]:
 cmd=[path('VASM'),*defs,'-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym']
 for inc in [Path(path('AMIGA_SHARE'))/'include',whd/'Include',whd/'Src/sources',Path(path('AMIGA_SHARE'))/'ndk/Include_I']:cmd.append('-I'+str(inc))
 cmd+=['-L',str(out/(mode+'.lst')),'-o',str(out/(mode+'.slave')),'RedBaronHD.s']
 subprocess.run(cmd,cwd=root/'src',check=True)
 b=(out/(mode+'.slave')).read_bytes();rows[mode]=dict(file_bytes=len(b),sha256=hashlib.sha256(b).hexdigest());print(mode,rows[mode],flush=True)
 if mode=='verify':assert rows[mode]['sha256']=='5c0918ccbccb27ad301478873e1aeab8398f057211b2749ce7d16fe949f23475'
 if mode!='verify':assert all(tag not in b for tag in (b'RBVERIFY',b'RBMIRR01',b'RBMCAC01'))
(out/'manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
