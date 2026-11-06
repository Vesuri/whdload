"""Guest differential fill tests: full guarded planes, edge outputs, original code."""
import os,sys,json,struct,subprocess,re,random
from pathlib import Path
from replay_flight import ROOT,run
out=Path(sys.argv[1]).resolve();os.chdir(ROOT)
cases=[]
r=random.Random(10)
spans=[(0,0),(0,31),(1,30),(31,32),(32,63),(17,291),(0,319),(319,319),(32,31)]
for kind in ['gouraud','texture','normal']:
 for i in range(256 if kind=='normal' else 90):
  l,rr=spans[i%len(spans)];height=1+i%5;y=10+i%170
  slope=0 if l in (0,319) or rr in (0,319) else (i%3-1)*16384
  if kind=='normal':rows=[]
  else:
   rows=[]
   for j in range(height):
    row=[l<<16,rr<<16]
    row+=([r.randrange(256)<<16,r.randrange(256)<<16] if kind=='gouraud' else [r.randrange(16)<<21,r.randrange(16)<<21,r.randrange(16)<<21,r.randrange(16)<<21])
    rows+=row
   rows += [1<<16,0]
  cases.append(dict(kind=kind,y=y,height=height,left=l<<16,right=rr<<16,slope=slope,color=i,rows=rows))

selected_only=bool(os.environ.get('SELECTED_ONLY'))
if selected_only:cases=cases[:180]
snapshot_cases=[87,177] if selected_only else [87,177,435]

def capture(cmd,dump,bases,hs,out):
 b=bases[0];code=b+0x8000
 # Guard each original entry independently, including the texture disassembly alignment.
 expected={0x4f840:'45ef0004280d',0x4f9f8:'9efc001848e73704',0x6c4f2:'23df0006c4c0'}
 for off,h in expected.items():assert hs[0]['bytes'][off:off+len(h)//2].hex()==h
 live={hex(o):dump(f'entry-{o:x}.bin',b+o,6).hex() for o in expected}
 assert all(live[hex(o)].startswith('4ef9') for o in ([0x4f840,0x4f9f8] if selected_only else expected)),live
 (out/'live-entries.json').write_text(json.dumps(live,indent=2))
 a=[' mc68040',f' org ${code:x}',' move.l #600000,d0',' move.l #$10001,d1',' move.l 4.w,a6',' jsr -198(a6)',' move.l d0,mem',' move.l d0,a0',' lea 128128(a0),a1',f' move.l a1,${b+0x55bec:x}',' move.w #16383,d7',' move.l #$00010203,d0','texinit:',' move.l d0,(a1)+',' add.l #$04040404,d0',' dbf d7,texinit',' move.l #$12345678,d0']
 # Preserve full outputs of three non-empty cases for an independent pixel oracle.
 for i,c in enumerate(cases):
  a += [f'case{i}:',' move.l mem(pc),a0',' move.l a0,a1',' lea 64064(a0),a2',' move.w #16015,d7',' move.l #$a55a6996,d0',f'init{i}:',' move.l d0,(a1)+',' move.l d0,(a2)+',' rol.l #3,d0',' add.l #$13ab,d0',f' dbf d7,init{i}']
  for side in [0,1]:
   a += [' move.l mem(pc),a0',f' lea {32+side*64064}(a0),a0',f' move.w ${bases[1]+0x4930:x},d0',f' move.l a0,(${b+0x4ce00:x},d0.w)']
   entry=f'original_{c["kind"]}' if side==0 else f'${b+{"gouraud":0x4f840,"texture":0x4f9f8,"normal":0x6c4f2}[c["kind"]]:x}'
   if c['kind']=='gouraud':
    a += [f' move.l #${v&0xffffffff:08x},-(sp)' for v in reversed(c['rows'])]
    a += [f' move.l #{c["y"]},a5',f' jsr {entry}',f' lea {len(c["rows"])*4}(sp),sp']
   elif c['kind']=='texture':
    a += [f' pea rows{i}',f' move.l #{c["y"]},-(sp)',f' jsr {entry}',' addq.l #8,sp']
   else:
    a += [f' move.l #{c["left"]},a2',f' move.l #{c["right"]},a3',f' move.l #{c["slope"]},a4',f' move.l #{-c["slope"]},a5',f' move.l #{c["y"]},a6',f' move.l #{c["height"]},d7',f' move.l #{c["color"]},d0',f' jsr {entry}',f' movem.l a2-a3,edges+{side*8}']
  a+=[' move.l mem(pc),a0',' lea 64064(a0),a1',' move.w #16015,d7',' moveq #0,d0',f'cmp{i}:',' move.l (a0)+,d1',' cmp.l (a1)+,d1',f' beq cmpnext{i}',' addq.l #1,d0',f'cmpnext{i}:',f' dbf d7,cmp{i}',f' move.l d0,results+{i*12}']
  if c['kind']=='normal':
   a+=[' move.l edges(pc),d0',' sub.l edges+8(pc),d0',f' move.l d0,results+{i*12+4}',' move.l edges+4(pc),d0',' sub.l edges+12(pc),d0',f' move.l d0,results+{i*12+8}']
  if i in snapshot_cases:
   k=snapshot_cases.index(i)
   a += [' move.l mem(pc),a0',f' lea {200000+k*128128}(a0),a1',' move.w #32031,d7',f'snapshot{i}:',' move.l (a0)+,(a1)+',f' dbf d7,snapshot{i}']
 a+=['finished:',' bra.s finished','original_gouraud:',' lea 4(sp),a2',' move.l a5,d4',f' jmp ${b+0x4f846:x}','original_texture:',' suba.w #24,sp',' movem.l d2-d3/d5-d7/a5,-(sp)',f' jmp ${b+0x4fa00:x}','original_normal:',f' move.l (sp)+,${b+0x6c4c0:x}',f' jmp ${b+0x6c4f8:x}','mem: dc.l 0','edges: ds.l 4']
 for i,c in enumerate(cases):
  if c['kind']=='texture':a += [f'rows{i}: dc.l '+','.join(f'${v&0xffffffff:08x}' for v in c['rows'])]
 a+=['results:',' ds.l '+str(len(cases)*3)]
 src=out/'fixture.s';src.write_text('\n'.join(a)+'\n');binary=out/'fixture.bin';symbols=out/'fixture.lst'
 subprocess.run(['bash','-c','. tools/env.sh; "$VASM" -quiet -Fbin -L "$3" -o "$2" "$1"','fixture',str(src),str(binary),str(symbols)],check=True)
 blob=binary.read_bytes();assert len(blob)<0x3b000,len(blob)
 listing=symbols.read_text();labels={n:int(re.search(r'^'+n+r'\s+A:([0-9A-Fa-f]+)',listing,re.M)[1],16) for n in ['finished','results','mem']}
 cmd('delete breakpoints');cmd('monitor tfxreg 16 2700')
 for off in range(0,len(blob),32):cmd(f'monitor tfxmem {code+off:x} {blob[off:off+32].hex()}')
 cmd(f'monitor tfxreg 17 {code:x}');cmd(f'break *{labels["finished"]:#x}')
 reply=cmd('continue');assert f'0x{labels["finished"]:08x}' in reply,reply
 cmd(f'monitor tfxsync {labels["results"]:x} {len(cases)*12}')
 data=dump('results.bin',labels['results'],len(cases)*12)
 for i,c in enumerate(cases):c['different_longs'],c['left_difference'],c['right_difference']=struct.unpack_from('>III',data,i*12)
 (out/'results.json').write_text(json.dumps(cases,indent=2))
 cmd(f'monitor tfxsync {labels["mem"]:x} 4')
 memory=struct.unpack('>I',dump('allocation.bin',labels['mem'],4))[0]
 cmd(f'monitor tfxsync {memory+200000:x} {len(snapshot_cases)*128128}')
 snapshots=dump('snapshots.bin',memory+200000,len(snapshot_cases)*128128)
 from render_oracle import expected_buffer
 oracle=[]
 for k,i in enumerate(snapshot_cases):
  expected=expected_buffer(cases[i]);original=snapshots[k*128128:k*128128+64064];native=snapshots[k*128128+64064:(k+1)*128128]
  oracle.append(dict(case=i,original_equal=original==expected,native_equal=native==expected,changed_bytes=sum(x!=y for x,y in zip(expected,expected_buffer(None)))))
 (out/'oracle.json').write_text(json.dumps(oracle,indent=2));assert all(x['original_equal'] and x['native_equal'] and x['changed_bytes'] for x in oracle),oracle
 failures=[c for c in cases if c['different_longs'] or c['left_difference'] or c['right_difference']]
 print('fill cases',len(cases),'failed',len(failures),flush=True)
 assert not failures,failures[:3]
v=dict(executable='tfx.020',custom3=3,custom4=18,swap=0x19fc,extra_args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true')
run('040',out,Path(str(out)+'-seed'),capture,v)
