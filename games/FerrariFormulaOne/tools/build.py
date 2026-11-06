#!/usr/bin/env python3
"""Build the single default-off SPS 0481 performance slave.
Requires vasm, WHDLoad sources, NDK includes, Python capstone and amitools.
The original game is only read for audited relocation metadata; never packaged.
All generated files go to the explicit output directory.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,struct,subprocess,sys
P=Path(__file__).resolve().parent; G=P.parent
# games/FerrariFormulaOne/tools/ with every source in ../src/, or the pre-import layout that
# tools/ff1layout.py stages: the host in Games/, the payload sources beside this script.
MAIN,FINE=(G/'src',G/'src') if P.name=='tools' and (G/'src').is_dir() else (G,P)
ap=argparse.ArgumentParser();ap.add_argument('--game',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True);a.game=a.game.resolve()
assert hashlib.sha256(a.game.read_bytes()).hexdigest()=='66ebd0939954329148e87c051fc041420d8f1ab4c2ad73ece7351b87ef9c889e','Verified SPS 0481 racemenu required'
vasm=os.environ.get('VASM',str(Path.home()/'.local/vasmm68k_mot'));whd=Path(os.environ['WHDLOAD']);ndk=Path(os.environ['NDK'])
def run(args,cwd):
 result=subprocess.run(args,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 (cwd/'build.log').write_text(result.stdout)
 if result.returncode:print(result.stdout);raise RuntimeError(args)
def symbols(path):return {n:int(v,16) for n,v in re.findall(r'^(\w+)\s+00:([0-9A-F]{8})$',path.read_text(errors='replace'),re.M)}
def host(offsets):
 (out/'payloads.i').write_text('\n'.join(f'{k} equ {v}' for k,v in offsets.items())+'\n')
 for name,target in [('SOURCES:Include',whd/'Include'),('Sources:whdload',whd/'Src/sources/whdload')]:
  p=out/name
  if not p.exists():p.symlink_to(target,target_is_directory=True)
 (out/'lvo').mkdir(exist_ok=True)
 for lib in ['exec','dos','graphics','expansion']:
  (out/'lvo'/f'{lib}.i').write_text(f' IFND FF1_LVO_{lib}\nFF1_LVO_{lib} SET 1\n INCLUDE "lvo/{lib}_lib.i"\n ENDC\n')
 run([vasm,f'-DFF1_EXPMEM_SIZE={EXPMEM}','-DFF1_PUBLIC_MEMORY=1','-DFF1_PUBLIC_LOADER=1','-DFF1_PUBLIC_STACK=1','-m68000','-pic','-x','-devpac','-Fhunkexe','-nosym',f'-I{out}',f'-I{FINE}',f'-I{MAIN}',f'-I{whd}/Include',f'-I{whd}/Src/sources',f'-I{ndk}','-L','host.list','-o','host.slave',str(MAIN/'FerrariFormulaOne_WHD.s')],out)
 return symbols(out/'host.list'),(out/'host.slave').read_bytes()
flags0=['FF1_PRODUCTION=1','FF1_PUBLIC_BINDINGS=1','FF1_PUBLIC_PATCHES=1','FF1_PUBLIC_MEMORY=1','FF1_RENDER_POSES=1']
flagsfine=['FF1_PRESENTATION_SPLIT=1','FF1_PRESENTATION_CALLBACK=1','FF1_PLAN_B=1','FF1_PLAYER_HOOKS=1','FF1_HELPERS_020=1','FF1_NATIVE_EXACT=5','FF1_PUBLIC_LIFECYCLE=1']
# Development-only fine-payload defines (FASTRAM_PLAN.md FR series), e.g.
# FF1_FINE_DEFINES=FF1_FAST_RENDER=1. Unset for production builds.
extra=[x for x in os.environ.get('FF1_FINE_DEFINES','').split(',') if x]
assert all(x.startswith('FF1_FAST_RENDER') for x in extra),extra
flagsfine+=extra
# ws_ExpMem: the 256 KiB Kickstart plus guest Fast. The Fast render mirrors
# (FASTRAM_PLAN.md FR4) need 256 KiB more guest Fast than production today.
EXPMEM=0x100000 if extra else 0xc0000
flags000=['FF1_COARSE_NATIVE_000=1','FF1_NATIVE_000_STAGE=3','FF1_COARSE_200=1','FF1_COARSE_200_COMPLETE=1']
flags000 += [x+'=1' for x in ['FF1_PRODUCT_AB','FF1_DIV200_AB','FF1_NATIVEMUL200_AB','FF1_RESET200_AB','FF1_CROSS200_AB','FF1_ROOTLEAD_AB','FF1_SMALLROOT_AB','FF1_C4_BLIT_GUARD','FF1_C4_ROAD_PREFETCH','FF1_C4_ROOT_SEED','FF1_C4_MUL_INLINE','FF1_C4_DIV_LIMIT','FF1_C4_MUL_WORD','FF1_C4_HOOK_P5','FF1_C4_CONTEXT_P5','FF1_C4_BOUNDARY_P5','FF1_C4_WAIT_IDLE','FF1_C4_COLOUR_ELIDE','FF1_C4_DIV_FAST','FF1_C4_ROTATE_FAST','FF1_C4_MUL_SITES','FF1_C4_SINE_INLINE','FF1_C4_NATIVE_FRAMES','FF1_C4_WAIT_DIRECT','FF1_C4_DIV_SHORT_FRAMES']]
def payload(kind,offset,hs):
 d=out/kind;d.mkdir(exist_ok=True)
 (d/'fine.s').write_text((FINE/('Fine.s' if kind=='fine' else 'Coarse.s')).read_text())
 for fn in ['bindings.bin','reset.bin']:(d/fn).write_bytes(bytes.fromhex('ffffffff'))
 flags=flags0+(flagsfine if kind=='fine' else ['FF1_COARSE_STEP=1']+(flags000 if kind=='000' else ['FF1_COARSE_020=1','FF1_COARSE_NATIVE_EXACT=1','FF1_NATIVE_EXACT=1']))
 flags += [f'FF1_HOST_CODE_SIZE={offset}',f'FF1_HOST_RESLOAD={hs["_resload"]}',f'FF1_HOST_ABORT={hs["FF1PerformanceAbort"]}',f'FF1_HOST_STACK={hs["FF1PublicStackOwner"]}',f'FF1_HOST_ATTN={hs["FF1ProfileAttn"]}',f'FF1_HOST_CACHE={hs["FF1CachePolicy"]}']
 args=[vasm,'-m68000' if kind=='000' else '-m68020','-Fbin','-quiet',f'-I{MAIN}',f'-I{FINE}']+['-D'+f for f in flags]+['-L','fine.list','-o','fine.bin','fine.s']
 run(args,d)
 run([sys.executable,str(P/'bindings.py'),str(d),str(a.game),kind],d)
 if kind=='fine':run([sys.executable,str(P/'reset.py'),str(d)],d)
 run(args,d);sy=symbols(d/'fine.list');data=bytearray((d/'fine.bin').read_bytes())
 if kind=='000':
  # Select the accepted R3g paths. These are immutable build presets, not
  # user-accessible A/B controls. No diagnostic entry or tape is included.
  values={'C4Enabled':1,'C4ResponseSkipEnabled':1,'C4ReturnSkipEnabled':1,'C4NativeHeading':1,'C4ProjectionSkipEnabled':1,'C4BlitEnabled':1,'C4RoadPrefetchEnabled':1,'C3Enabled':3}
  for n in ['FF1ProductControl','FF1Div200Control','FF1NativeMul200Control','FF1Reset200Control','FF1Cross200Control','FF1RootLeadControl','FF1SmallRootControl','C4RootSeedControl','FF1MulInlineControl','FF1DivLimitControl','C4BoundaryControl','C4WaitIdleControl','C4ColourControl','FF1C4MulSitesControl','C4WaitDirectControl']:values[n]=0
  for n,v in values.items():struct.pack_into('>H',data,sy[n],v)
  for n in ['FF1NativeMulP4Gate']+['C4P5Gate_'+n for n in ['velocity_671e6','bridge_6720e','bridge_68546','velocity_68576','velocity_6721c','velocity_685a6']]:data[sy[n]:sy[n]+4]=bytes.fromhex('4e714e71')
  struct.pack_into('>H',data,sy['C4P5RotateSave']+2,0xf8c0);struct.pack_into('>H',data,sy['C4P5RotateRestore']+2,0x031f)
  for gate,target in [('FF1DivFastGate','FF1C4DividePositive'),('C4RotateDispatch','C4RotateFast'),('C4RotateWordXGate','C4RotateWordXFast'),('C4RotateWordZGate','C4RotateWordZFast'),('C4Sine1Gate','C4Sine1Fast'),('C4Sine2Gate','C4Sine2Fast'),('C4ProductFrameGate','C4ProductFrameSelected'),('FF1NativeFrameGate','FF1NativeFrameFast'),('FF1C4DivideShortGate','FF1C4DivideShortFast')]:
   data[sy[gate]:sy[gate]+2]=bytes.fromhex('6000');struct.pack_into('>h',data,sy[gate]+2,sy[target]-sy[gate]-2)
  for n in ['public_table','public_bound','public_bindings','FF1ApplyBindings','FF1PatchBegin','FF1PatchSeal']:
   assert -32768<=sy[n]-sy['FF1VelocityRotate000']<=32767,(n,'68000 anchor overflow')
 for item in json.loads((d/'bindings.json').read_text()):assert struct.unpack_from('>H',data,item['offset'])[0]==item['expected'],item
 data+=bytes((-len(data))%4);(d/'payload.bin').write_bytes(data)
 return sy,data
initial={'FF1_FINE_OFFSET':0,'FF1_020_OFFSET':0,'FF1_000_OFFSET':0,'FF1_FINE_SELECTION':0}
hs,h=host(initial);offset=len(h)-36;parts=[];meta={};defs={}
for kind in ['000','020','fine']:
 sy,data=payload(kind,offset,hs);defs['FF1_'+kind.upper()+'_OFFSET']=offset
 meta[kind]={'offset':offset,'bytes':len(data),'symbols':sy,'sha256':hashlib.sha256(data).hexdigest()};parts.append(data);offset+=len(data)
 if kind=='fine':defs['FF1_FINE_SELECTION']=sy['selection_path']
check,final=host(defs);assert len(h)==len(final) and hs==check,'Host layout must be independent of payload offsets'
code=bytearray(final[32:-4]);struct.pack_into('>H',code,24,hs['FF1ProductionBoot']);struct.pack_into('>I',code,32,EXPMEM)
for data in parts:code+=data
# $VER (docs/releasing.md) after the payloads, so no host or payload offset moves; the
# version and date are slv_info's.
ver=re.search(r'"Version (\S+ \(\d\d\.\d\d\.\d{4}\))"',(MAIN/'FerrariFormulaOne_WHD.s').read_text(errors='replace')).group(1)
code+=f'$VER: FerrariFormulaOne.slave {ver}'.encode()+b'\0';code+=bytes((-len(code))%4)
header=bytearray(final[:32]);struct.pack_into('>I',header,20,len(code)//4);struct.pack_into('>I',header,28,len(code)//4)
result=header+code+bytes.fromhex('000003f2');(out/'FerrariFormulaOne.slave').write_bytes(result)
(out/'build.json').write_text(json.dumps({'sha256':hashlib.sha256(result).hexdigest(),'bytes':len(result),'host_bytes':len(final)-36,'host_symbols':hs,'payloads':meta,'game_sha256':hashlib.sha256(a.game.read_bytes()).hexdigest()}|({'fine_defines':extra} if extra else {}),indent=2)+'\n')
print('Built',len(result),'bytes:',hashlib.sha256(result).hexdigest())
