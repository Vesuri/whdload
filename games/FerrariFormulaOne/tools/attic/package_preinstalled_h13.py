"""Local Retroplay-based preinstalled candidate; game data stays ignored."""
from pathlib import Path
import hashlib,json,os,struct,subprocess,tempfile
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
base=r/'tmp/archives/FerrariFormulaOne_v1.01_0481.lha'
out=r/'dist/FerrariFormulaOne_v1.02-h13_0481_Performance.lha';out.parent.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
original_sha=sha(base.read_bytes())
lha=os.environ['LHA'];candidate=r/'tmp/release/FerrariFormulaOne-1.02-h13'
slave=(candidate/'FerrariFormulaOne.slave').read_bytes()
assert sha(slave)=='8b45d6a893ea3b29f3543e66147c3fcb419883c67cbdbfb15d981fe25078f1fd'
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

intro='Ferrari Formula One 1.02 H13 - local development preinstalled build\n================================================================\n\nBased on Retroplay FerrariFormulaOne_v1.01_0481. Original game data,\nmanual and artwork are preserved. Includes the accepted rendering changes\nthrough H13 and the RC2 driving-control fix. H1 and H12 are excluded.\nThis is a development snapshot, not a newly release-qualified RC.\n\nExtract the entire drawer. WHDLoad and required Kickstart support must already\nbe installed. Double-click Performance for the improved simulation/rendering,\nor FerrariFormulaOne for legacy mode. Alternatively use Execute\nLaunch-Performance or Execute Launch-Legacy. F10 exits.\n\nPerformance uses CUSTOM2=1; the normal icon uses CUSTOM2=0. Both retain PRELOAD\nand set NoWriteCache, ConfigDelay=0 and SplashDelay=0, as required by the tested\nemulator save/load and chip-only startup routes.\n\nEnabled PAL SPS 0481: 68000 uses 200 ms simulation updates; chip-only 020 uses\nnative 100 ms; 020+Fast and faster use 20 ms player/100 ms opponents.\nRendering is separate. The added H10/H13 CPU drawing paths select 030 and faster.\n\nThe slave reserves 768 KiB expansion plus 512 KiB Chip, the 267064-byte slave\nand OS/runtime overhead. 020+Fast testing uses 2 MiB Chip + 4 MiB Fast;\naccelerated testing uses 2 MiB Chip + 8 MiB Fast. See Qualification.txt for\nother tested configurations and historical limitations. Enabled NTSC is\nrejected; Irek remains on its original untested route.\n\nQualification.txt distinguishes the current reduced H-series checks from\nhistorical release qualification. BuildInfo.json identifies exact source and\nslave bytes. Human full-race playtesting and real hardware testing are deferred.\nThe inherited B8-PAL border-colour diagnostic pulse remains; its cleanup is\nseparate. Universal 25 FPS is not achieved. Nothing has been published.\n\nThe original v1.01 ReadMe follows unchanged. Its version and memory statements\nrefer to the original slave.\n\n--------------------------------------------------------------------------\n\n'
for a,b in [('WHDLoad20.1','WHDLoad 20.1'),('SPS0481','SPS 0481'),('uses200ms','uses 200 ms'),('chip-only020','chip-only 020'),('native100ms','native 100 ms'),('qualified020','qualified 020'),('uses20ms','uses 20 ms'),('reserves768KiB','reserves 768 KiB'),('plus512KiB','plus 512 KiB'),('the260276-byte','the 260276-byte'),('A500512KiB','A500 512 KiB'),('with2MiB','with 2 MiB'),('uses2MiB','uses 2 MiB'),('use2MiB','use 2 MiB'),('WHDLoad17.0','WHDLoad 17.0')]:intro=intro.replace(a,b)
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
 (r/'manifest/preinstalled-h13.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
