from pathlib import Path
import json,re
r=Path(__file__).resolve().parents[1]; repo=r.parents[1]; games=repo/'Games'; p=games/'FerrariFormulaOne';p.mkdir(exist_ok=True)
# Keep the independent payloads in their accepted instruction-set domains.
f=(r/'tmp/build/step5-b8-v3/lean/fine.s').read_text()
f=re.sub(r'include "[^"\n]*/Games/([^"\n]+)"',r'include "\1"',f)
a=f.index('verifydiv:');b=f.index('modeval:',a);f=f[:a]+f[b:]
a=f.index('selection_boot:');b=f.index(' include "FerrariFormulaOne_UpdateHooks.s"',a)
f=f[:a]+'''selection_path: dc.l 2
selection_interval: dc.l 20
 include "FerrariFormulaOne_Profile.s"
'''+f[b:]
a=f.index('s2_rng_control:');b=f.index('FF1PresentationAfterTick:',a);f=f[:a]+f[b:]
f=f.replace(' move.w #$4eb9,$6a304\n lea s2_rng_control(pc),a1\n move.l a1,$6a306\n','')
f=f.replace(' lea (ticks.l,pc),a0\n addq.l #1,(a0)\n cmpi.l #126,(a0)\n bne.w finish',' tst.l schedule_context+FF1T_STEP_MS(pc)\n bne.w finish') # corrected to word later
f=f.replace(' tst.l schedule_context+FF1T_STEP_MS(pc)',' tst.w schedule_context+FF1T_STEP_MS(pc)')
f=f.replace(' bsr.w schedule_install',' bsr.w FF1FinePauseInstall\n bsr.w schedule_install')
a=f.index(' cmpi.w #2,d0\n blo.w finish',f.index('barrier:'));b=f.index(' bsr.l public_seal',a)
f=f[:a]+f[b:]
f=f.replace(' include "b8draw.s"',' include "FerrariFormulaOne_FullPresentation.s"')
f=f.replace('#6384','#FF1_HOST_CODE_SIZE').replace('move.l $1180(a2),a2','move.l FF1_HOST_RESLOAD(a2),a2').replace('6358+4(a0)','FF1_HOST_STACK+4(a0)').replace('6358(a0)','FF1_HOST_STACK(a0)')
f=f.replace("public_marker: dc.b 'FF1B7BOUNDHOOK',0",'public_marker: dc.b "FF1FINE",0')
f+='\n include "FinePause.s"\n'
(p/'Fine.s').write_text('; Production 68020+Fast entry; SPS 0481 bindings are generated at build time.\n'+f)
coarse=(r/'tmp/build/step5-c4-divide-frame-r3g-v1-ab/000/fine.s').read_text()
a=coarse.index('selection_boot:');b=coarse.index(' include "FerrariFormulaOne_Coarse.s"',a)
coarse=coarse[:a]+'''selection_path: dc.l 1
selection_interval: dc.l 100
'''+coarse[b:]
coarse=coarse.replace(' include "FerrariFormulaOne_Coarse200RootTable.s"',' IFD FF1_COARSE_200_COMPLETE\n include "FerrariFormulaOne_Coarse200RootTable.s"')+'\n ENDC\n'
(p/'Coarse.s').write_text('; Production coarse entries: 68000 200 ms / chip-only 68020 100 ms.\n'+coarse)
# Build-time canonical addresses are identities only; runtime addresses always
# come from the native loader. No game bytes or emulation snapshots are stored.
mp=json.loads((r/'manifest/step2-overlays.json').read_text())
layout={h['number']:{k:h[k] for k in ('base','size')} for g in mp['groups'] for h in g['hunks']}
(p/'layout.json').write_text(json.dumps(layout,indent=2)+'\n')
# Generalize the binding engine to a supplied original game, with explicit
# relocation decoding independent of an emulated runtime memory dump.
s=(r/'tools/build_step5_b7_bindings.py').read_text();a=s.index('from overlay_map import catalog');b=s.index('def hunk(v):')
s=s[:a]+'''from native import catalog
root=Path(__file__).resolve().parent
b=Path(sys.argv[1]); game=Path(sys.argv[2]); kind=sys.argv[3]
code=(b/'fine.bin').read_bytes();listing=(b/'fine.list').read_text()
symbols={n:int(v,16) for n,v in re.findall(r'^(\\w+)\\s+00:([0-9A-F]{8})$',listing,re.M)}
hunks={int(k):dict(v,number=int(k)) for k,v in json.loads((root/'layout.json').read_text()).items()}
native=bytearray(0x80000);relocs={}
for group in catalog(game):
 if group['header'] not in (0,0x22f30,0x30a30,0x30a7c):continue
 for h in group['hunks']:
  base=hunks[h['number']]['base'];native[base:base+len(h['data'])]=h['data']
  for dest,offs in h['reloc'].items():
   for off in offs:
    at=base+off;value=struct.unpack_from('>I',native,at)[0]+hunks[dest]['base']
    struct.pack_into('>I',native,at,value);relocs[at]=value
c=Cs(CS_ARCH_M68K,CS_MODE_BIG_ENDIAN|CS_MODE_M68K_020);c.detail=True
records={};why={}
'''+s[b:]
s=s.replace("symbols['schedule_install']","symbols.get('schedule_install',symbols.get('FF1MultiplyU64_000',0))")
a=s.index("p=symbols['FF1NativeSites']");b=s.index('# Review explicit',a)
s=s[:a]+'''if kind in ('fine','020'):
 p=symbols['FF1NativeSites']
 while True:
  start=struct.unpack_from('>I',code,p)[0]
  if not start:break
  size,tag=struct.unpack_from('>HH',code,p+4)
  addlong(p,start,'native site address');fragment(p+8,start,size,'native site signature');p+=8+size
if kind in ('fine','000'):
 prefix='' if kind=='fine' else '000'
 fragment(symbols['FF1Track'+prefix+'Signature'],0x6977a,0x112,'lookahead signature')
 fragment(symbols['FF1Track'+prefix+'Signature']+0x112,0x67514,0x16,'lookahead caller')
 fragment(symbols['FF1Trig'+prefix+'Signature'],0x24fe0,64,'trig signature')
if kind=='000':
 fragment(symbols['FF1C4ColourSignature'],0x32d48,0x1c8,'colour signature')
 for label,address,length in [('1',0x6759a,22),('2',0x6ea2c,12),('3',0x6cd54,16)]:
  fragment(symbols['FF1C4MulSiteSignature'+label],address,length,'multiply signature')
'''+s[b:]
s=s.replace("if not symbols['velocity_671e6']<=pc<", "if not symbols.get('velocity_671e6',0)<=pc<")
a=s.index('for line in listing.splitlines():',s.index('data_candidates=[]'));b=s.index("(b/'bindings-data-review.json')",a);s=s[:a]+s[b:]
(p/'bindings.py').write_text(s)
s=(r/'tools/overlay_map.py').read_text();a=s.index('def catalog():');b=s.index('\ndef decode',a)
s='from pathlib import Path\nimport struct\nfrom amitools.binfmt.hunk.HunkReader import HunkReader\n'+s[a:b]
s=s.replace('def catalog():','def catalog(game):').replace("ROOT/'tmp/game/FerrariFormulaOne_v1.01_0481/FerrariFormulaOne/data/racemenu'",'game')
(p/'native.py').write_text(s)
s=(r/'tools/build_step5_b7_reset.py').read_text().replace("sy['selection_tags']<=pc<sy['selection_enabled']+4","sy['selection_path']<=pc<sy['selection_interval']+4")
(p/'reset.py').write_text(s)
# Source-level production switches retain every existing diagnostic build.
def edit(name,old,new):
 path=games/name;s=path.read_text();assert old in s,(name,old);path.write_text(s.replace(old,new))
for name in ('FerrariFormulaOne_CoarseInstall.s','FerrariFormulaOne_PublicLifecycle.s','FerrariFormulaOne_UpdateHooks.s'):
 edit(name,' move.l $1180(a2),a2',' IFD FF1_PRODUCTION\n move.l FF1_HOST_RESLOAD(a2),a2\n ELSE\n move.l $1180(a2),a2\n ENDC')
edit('FerrariFormulaOne_CoarseInstall.s',' move.w #$4eb9,$6a304\n lea s2_rng_control(pc),a0\n move.l a0,$6a306',' IFND FF1_PRODUCTION\n move.w #$4eb9,$6a304\n lea s2_rng_control(pc),a0\n move.l a0,$6a306\n ENDC')
edit('FerrariFormulaOne_CoarseInstall.s',' IFD FF1_C4_NATIVE_FRAMES\n; WHDLoad',' IFND FF1_PRODUCTION\n IFD FF1_C4_NATIVE_FRAMES\n; WHDLoad')
edit('FerrariFormulaOne_CoarseInstall.s','C1Flush:\n',' ENDC\nC1Flush:\n')
edit('FerrariFormulaOne_Coarse.s',' lea C1Heads(pc),a0\n addq.l #1,(a0)\n cmpi.l #126,(a0)\n bne.b .existing',' IFD FF1_PRODUCTION\n tst.w C1Active(pc)\n bne.b .existing\n ELSE\n lea C1Heads(pc),a0\n addq.l #1,(a0)\n cmpi.l #126,(a0)\n bne.b .existing\n ENDC')
edit('FerrariFormulaOne_Coarse.s',' lea s2_rng_done(pc),a0\n clr.w (a0)',' IFND FF1_PRODUCTION\n lea s2_rng_done(pc),a0\n clr.w (a0)\n ENDC')
edit('FerrariFormulaOne_UpdateHooks.s',' cmpi.l #126,ticks(pc)\n blo.b .done',' IFND FF1_PRODUCTION\n cmpi.l #126,ticks(pc)\n blo.b .done\n ENDC')
edit('FerrariFormulaOne_UpdateHooks.s',' cmpi.l #126,ticks(pc)\n blo.w .done',' IFND FF1_PRODUCTION\n cmpi.l #126,ticks(pc)\n blo.w .done\n ENDC')
# Coarse diagnostic counters have no scheduling role.
for label in ('C1Completed','C1Skipped'):
 edit('FerrariFormulaOne_Coarse.s',f' lea {label}(pc),a0\n addq.l #1,(a0)',f' IFND FF1_PRODUCTION\n lea {label}(pc),a0\n addq.l #1,(a0)\n ENDC')
edit('FerrariFormulaOne_FullPresentation.s',' IFD FF1_COARSE_STEP\n lea B8Frames(pc),a0',' IFND FF1_PRODUCTION\n IFD FF1_COARSE_STEP\n lea B8Frames(pc),a0')
edit('FerrariFormulaOne_FullPresentation.s',' addq.l #1,(a0)\n move.l -60(a6),$226ae',' addq.l #1,(a0)\n ENDC\n move.l -60(a6),$226ae')
print('Prepared production source components')
