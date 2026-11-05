"""Local Retroplay-based preinstalled candidate; game data stays ignored."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,tempfile
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
base=r/'tmp/archives/FerrariFormulaOne_v1.01_0481.lha'
out=r/'dist/FerrariFormulaOne_v1.02-rc1_0481_Performance.lha';out.parent.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
original_sha=sha(base.read_bytes())
lha=os.environ['LHA'];candidate=r/'tmp/release/FerrariFormulaOne-1.02-rc1'
slave=(candidate/'FerrariFormulaOne.slave').read_bytes()
assert sha(slave)=='60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836'
def run(args,**kw):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw)
 if p.returncode:raise RuntimeError(p.stdout.decode(errors='replace')[-3000:])
 return p.stdout

def icon_parts(b):
 # Adapted from Test Drive2's established DiskObject packager.
 assert b[:4]==bytes.fromhex('e3100001')
 select=struct.unpack_from('>I',b,26)[0]
 default_tool,tool_types=struct.unpack_from('>II',b,50)
 p=78+(56 if struct.unpack_from('>I',b,66)[0] else 0)
 for _ in range(2 if select else 1):
  w,h,d=struct.unpack_from('>HHH',b,p+4);p+=20+(w+15)//16*2*h*d
 tool=None
 if default_tool:
  n=struct.unpack_from('>I',b,p)[0];tool=b[p+4:p+4+n-1];p+=4+n
 assert tool_types and tool==b'WHDLoad'
 start=p;n=struct.unpack_from('>I',b,p)[0]//4-1;p+=4;types=[]
 for _ in range(n):
  size=struct.unpack_from('>I',b,p)[0];assert b[p+4+size-1]==0
  types.append(b[p+4:p+3+size]);p+=4+size
 return start,p,types

def unpositioned(b):
 result=bytearray(b);struct.pack_into('>II',result,58,0x80000000,0x80000000)
 assert bytes(result[:58])+bytes(result[66:])==b[:58]+b[66:]
 return bytes(result)

def icon_options(original,options):
 start,end,types=icon_parts(original)
 assert all(not any(t.upper().split(b'=')[0]==o.split(b'=')[0] for t in types) for o in options)
 at=types.index(b'PRELOAD')+1;new=types[:at]+options+types[at:]
 table=struct.pack('>I',(len(new)+1)*4)+b''.join(struct.pack('>I',len(t)+1)+t+b'\0' for t in new)
 result=original[:start]+table+original[end:]
 ns,ne,parsed=icon_parts(result);assert parsed==new
 assert result[:ns]==original[:start] and result[ne:]==original[end:]
 assert parsed[:at]+parsed[at+len(options):]==types
 return result

intro='''Ferrari Formula One 1.02 RC1 - modified preinstalled candidate
============================================================

This local package is based on Retroplay's FerrariFormulaOne_v1.01_0481.
Its original game data, manual and icon artwork are preserved. The slave is
replaced with our emulator-qualified production build. Nothing is published.
Human playtesting and real Amiga hardware testing remain deferred.

Extract the complete drawer to your Amiga games drive. WHDLoad and its required
Kickstart support must already be installed, as with the Retroplay original.

Double-click Performance to enable the modified elapsed-time simulation.
Double-click FerrariFormulaOne for legacy mode (the default-off behavior).
The Performance icon sets CUSTOM2=1; the normal icon sets CUSTOM2=0.
Both icons retain PRELOAD and add NoWriteCache, ConfigDelay=0 and SplashDelay=0.
NoWriteCache is required for the qualified emulator save/load route; the splash
settings are required on the tested chip-only 020 with WHDLoad20.1.

Alternatively, from this drawer use Execute Launch-Performance or
Execute Launch-Legacy. F10 exits. CUSTOM1 retains its original meaning only in
legacy mode; the performance mode supersedes the original timing repair.

Enabled PAL SPS0481: 68000 uses200ms simulation updates; chip-only020 uses the
native100ms step; qualified020+Fast uses20ms player/100ms opponents. Rendering
is separate. There is no performance-triggered A500 fallback.

The modified slave reserves768KiB expansion plus512KiB Chip, the260292-byte
slave and OS/runtime overhead. This supersedes the old memory requirements
below. Tested WHDLoad20.1 configurations include A500512KiB Chip+1.5MiB Slow,
A500512KiB Chip+2MiB Fast without Slow, and chip-only020 with2MiB Chip and both
splashes off. 020+Fast uses2MiB Chip+4MiB Fast; accelerated tests use2MiB Chip+
8MiB Fast. WHDLoad17.0 functional checks pass with Fast memory; the tested
Chip/Slow-only arrangements fail allocation there. No universal minimum or
original-release memory equivalence is claimed.

Enabled NTSC is rejected. Irek remains on the original route and is not tested.
Qualification.txt contains the detailed checks, measurements and limitations.
BuildInfo.json identifies the exact source and slave. All game data is unchanged.

The historical v1.01 ReadMe follows unchanged. Its memory and version statements
refer to the original slave, not this larger modified build.

--------------------------------------------------------------------------

'''
for a,b in [('WHDLoad20.1','WHDLoad 20.1'),('SPS0481','SPS 0481'),('uses200ms','uses 200 ms'),('chip-only020','chip-only 020'),('native100ms','native 100 ms'),('qualified020','qualified 020'),('uses20ms','uses 20 ms'),('reserves768KiB','reserves 768 KiB'),('plus512KiB','plus 512 KiB'),('the260292-byte','the 260292-byte'),('A500512KiB','A500 512 KiB'),('with2MiB','with 2 MiB'),('uses2MiB','uses 2 MiB'),('use2MiB','use 2 MiB'),('WHDLoad17.0','WHDLoad 17.0')]:intro=intro.replace(a,b)
with tempfile.TemporaryDirectory(prefix='preinstalled-',dir=r/'tmp') as td:
 stage=Path(td)/'stage';stage.mkdir();run(['/opt/homebrew/bin/lha',f'xqw={stage}',str(base)])
 before={str(p.relative_to(stage)):p.read_bytes() for p in stage.rglob('*') if p.is_file()};assert len(before)==47
 top=stage/'FerrariFormulaOne';original_icon=(top/'FerrariFormulaOne.info').read_bytes()
 common=[b'NoWriteCache',b'ConfigDelay=0',b'SplashDelay=0']
 (top/'FerrariFormulaOne.info').write_bytes(icon_options(original_icon,[b'CUSTOM2=0']+common))
 (top/'Performance.info').write_bytes(unpositioned(icon_options(original_icon,[b'CUSTOM2=1']+common)))
 (top/'FerrariFormulaOne.slave').write_bytes(slave)
 (top/'ReadMe').write_bytes(intro.replace('\n','\r\n').encode('ascii')+before['FerrariFormulaOne/ReadMe'])
 (top/'Qualification.txt').write_bytes((candidate/'RELEASE_QUALIFICATION.md').read_bytes())
 for name in ['BuildInfo.json','Launch-Performance','Launch-Legacy']:(top/name).write_bytes((candidate/name).read_bytes())
 # ReadMe's project icon uses the text viewer and carries no filename binding.
 (top/'Qualification.txt.info').write_bytes(unpositioned(before['FerrariFormulaOne/ReadMe.info']))
 after={str(p.relative_to(stage)):p.read_bytes() for p in stage.rglob('*') if p.is_file()}
 changed=sorted(n for n in before if before[n]!=after[n]);added=sorted(set(after)-set(before))
 assert changed==['FerrariFormulaOne/FerrariFormulaOne.info','FerrariFormulaOne/FerrariFormulaOne.slave','FerrariFormulaOne/ReadMe']
 assert added==sorted('FerrariFormulaOne/'+n for n in ['Performance.info','Qualification.txt','Qualification.txt.info','BuildInfo.json','Launch-Performance','Launch-Legacy'])
 assert set(before)<=set(after)
 data=[n for n in before if n.startswith('FerrariFormulaOne/data/')];assert len(data)==40
 assert all(before[n]==after[n] for n in data)
 for p in stage.rglob('*'):
  if p.is_file():os.chmod(p,0o644)
  if p.is_file() and (str(p.relative_to(stage)) in added or str(p.relative_to(stage)) in changed):os.utime(p,(1791936000,1791936000))
 temp_archive=Path(td)/out.name
 run([lha,'a1o5q2',str(temp_archive),*sorted(after)],cwd=stage)
 run([lha,'t',str(temp_archive)])
 check=Path(td)/'check';check.mkdir();run(['/opt/homebrew/bin/lha',f'xqw={check}',str(temp_archive)])
 extracted={str(p.relative_to(check)):p.read_bytes() for p in check.rglob('*') if p.is_file()}
 assert extracted==after
 assert all(len(Path(n).name)<=30 for n in after)
 assert sha(base.read_bytes())==original_sha
 out.write_bytes(temp_archive.read_bytes())
 report={'status':'passed','base':str(base.relative_to(r)),'base_sha256':original_sha,'archive':str(out.relative_to(r)),'archive_sha256':sha(out.read_bytes()),'archive_bytes':out.stat().st_size,'format':'LHa level1 LH5','members':len(after),'unchanged_game_files':len(data),'changed':changed,'added':added,'slave_sha256':sha(slave),'default_icon_custom2':0,'performance_icon_custom2':1,'icon_artwork_and_original_tooltypes_preserved':True,'new_icons_use_automatic_placement':True,'crc_test_passed':True,'full_reextract_exact':True,'published':False,'files':{n:sha(b) for n,b in sorted(after.items())}}
 (r/'manifest/preinstalled-rc1.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
