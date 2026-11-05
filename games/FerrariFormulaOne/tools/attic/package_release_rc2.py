"""Package already-qualified bytes; never include game/runtime data or publish."""
from pathlib import Path
import hashlib,io,json,subprocess,zipfile
r=Path(__file__).resolve().parents[1];repo=r.parents[1]
name='FerrariFormulaOne-1.02-rc2';out=r/'tmp/release'/name;out.mkdir(parents=True,exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
audit=json.loads((r/'manifest/drive-final-artifact-audit.json').read_text());slave=(r/'tmp/build/drive-fix/FerrariFormulaOne.slave').read_bytes();assert sha(slave)==audit['production_sha256'];assert int.from_bytes(slave[44:46],'big')==17
for file,digest in audit['source_hashes'].items():assert sha((repo/file).read_bytes())==digest
info={'candidate':name,'scope':'RC2 launch-speed correction and native driving-control regressions; historical qualification scopes documented; full human races and real hardware deferred','source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'source_hashes':audit['source_hashes'],'slave_sha256':sha(slave),'slave_bytes':len(slave),'required_whdload_api':17,'vasm_sha256':audit['toolchain']['vasm']['sha256'],'python':audit['toolchain']['python'],'game_input_sha256':json.loads((r/'tmp/build/drive-fix/build.json').read_text())['game_sha256'],'default_mode':'legacy, CUSTOM2=0','published':False}
readme='''Ferrari Formula One 1.02 RC2 release candidate 2

Unreleased, opt-in, emulator-qualified candidate for the SPS 0481 PAL game.
Human playtesting and real Amiga hardware testing are deferred.

RC2 fixes the 20ms launch-speed cutoff that prevented acceleration from rest.
Native throttle, clutch, brake, steering and manual gears are tested; see the
appended controls regression report for the corrected-binary evidence.

Installation: back up your existing FerrariFormulaOne.slave, then copy this
slave into an existing legally installed Ferrari Formula One game drawer.
Keep its existing data drawer. No game data, Kickstart or WHDLoad is included.
Run scripts from that game drawer with Execute Launch-Performance or
Execute Launch-Legacy. WHDLoad must be installed and available on the command
path. These scripts do not modify global preferences or game files themselves.

CUSTOM2=0 is the slave default: original loop; CUSTOM1 retains its timing-repair
meaning. CUSTOM2=1 enables the new mode. Both CUSTOM1 settings then have the
same performance behavior. 68000 uses 200ms updates, chip-only 020 uses native
100ms, and qualified 020+Fast uses 20ms player/100ms opponents. Rendering and
simulation are separate. CPU-only allocations are public; DMA stays Chip.
There is no performance-triggered A500 fallback.

Launch scripts include NoWriteCache: required by the qualified save/load route
on the tested emulator/directory-drive configuration. They also disable both
configuration/startup splashes, required for tested chip-only 020 on WHDLoad 20.1.
These are scoped emulator workarounds, not claims of a real-hardware defect.

Memory/runtime scope: the slave reserves 768KiB expansion plus 512KiB Chip,
the 260276-byte slave and OS/runtime overhead. Original minimum memory is not
preserved. WHDLoad 20.1 passes with A500 512KiB Chip+1.5MiB Slow, or 512KiB Chip+
2MiB Fast without Slow; chip-only 020 passes with 2MiB Chip and both splashes off.
020+Fast uses 2MiB Chip+4MiB Fast; accelerated tests use 2MiB Chip+8MiB Fast.
WHDLoad 17.0 passes functional checks with Fast memory on 000/020/060; tested
Chip/Slow-only arrangements fail allocation there. Smaller machines tested
also fail. This is not a universal minimum across every OS/runtime setup.

Enabled NTSC is rejected. Unavailable Irek retains the original route and has
not been runtime-qualified. F10 exits. See RELEASE_QUALIFICATION.md for complete
scope, native controls/save/clock evidence and measured performance. BuildInfo
and SHA256SUMS identify the exact candidate. No package has been published.
'''
files={'FerrariFormulaOne.slave':slave,'ReadMe':readme.encode(),'RELEASE_QUALIFICATION.md':(repo/'Games/FerrariFormulaOne/RELEASE_QUALIFICATION.md').read_bytes()+b'\n\n'+(repo/'Games/FerrariFormulaOne/CONTROLS_REGRESSION.md').read_bytes(),'BuildInfo.json':(json.dumps(info,indent=2)+'\n').encode()}
for mode,custom in [('Performance',1),('Legacy',0)]:files['Launch-'+mode]=f'WHDLoad FerrariFormulaOne.slave PRELOAD CUSTOM1=0 CUSTOM2={custom} ConfigDelay=0 SplashDelay=0 NoWriteCache\n'.encode()
files['SHA256SUMS']=(''.join(f'{sha(data)}  {file}\n' for file,data in sorted(files.items()))).encode()
assert set(p.name for p in out.iterdir())<=set(files),'Unexpected existing package files'
for file,data in files.items():(out/file).write_bytes(data)
def archive():
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for file,data in sorted(files.items()):
   zi=zipfile.ZipInfo(name+'/'+file,(2026,10,14,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zi.external_attr=(0o100644<<16);z.writestr(zi,data)
 return stream.getvalue()
a=archive();assert a==archive();target=out.parent/(name+'.zip');target.write_bytes(a)
with zipfile.ZipFile(io.BytesIO(a)) as z:
 assert set(z.namelist())=={name+'/'+x for x in files}
 for file,data in files.items():assert z.read(name+'/'+file)==data
report={'status':'passed','directory':str(out.relative_to(r)),'archive':str(target.relative_to(r)),'archive_sha256':sha(a),'archive_bytes':len(a),'deterministic_archive_exact':True,'source_revision':info['source_revision'],'production_sha256':sha(slave),'files':{file:{'bytes':len(data),'sha256':sha(data)} for file,data in files.items()},'no_game_or_runtime_data':True,'published':False}
(r/'manifest/release-candidate-rc2.json').write_text(json.dumps(report,indent=2)+'\n');print('Packaged',target,len(a),'bytes',sha(a))
