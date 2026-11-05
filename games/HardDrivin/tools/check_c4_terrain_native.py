from pathlib import Path
import ctypes as C,json,os,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
sys.path.insert(0,'tools');from game_image import hunks
root=Path('tmp/prof/c4-continued-loop-slow');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];sp=0x4f000;stop=code+0xcdf6
images=[(addr,(root/f'timing-state-{name}.bin').read_bytes()) for name,addr in [('chip',0),('slow',0xc00000)]]
listing=Path('tmp/build/c4-continued-loop.lst').read_text(encoding='latin1');sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)};base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()}
sy.update({new:sy[old] for old,new in {'_private_terrain_select': '_terrain_select', '_private_road_selected_hook': '_terrain_selected_hook', '_private_road_selected': '_terrain_selected', '_private_road_continuing': '_terrain_continuing', '_private_road_mask': '_terrain_mask', '_private_road_bounds': '_terrain_bounds', '_private_road_indices': '_terrain_indices'}.items()})
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
sy['_terrain_select']-=0x1000
s=Path('src/HardDrivinTerrain.s').read_text();body=s[s.index('_terrain_select:'):s.index('; Preserve the displaced native writes')];blobs=[]
for forced in [False,True]:
 stem=Path('tmp/c4-terrain-native-'+str(forced));symbols='\n'.join('%s equ $%x'%(k,v) for k,v in sy.items() if k!='_terrain_select');stem.with_suffix('.s').write_text(' org $%x\n'%sy['_terrain_select']+('VERIFY_DISPATCH_NATIVE equ 1\n' if forced else '')+symbols+'\n'+body);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);blobs.append(stem.with_suffix('.bin').read_bytes())
count=0;volatile=set()
try:
 for forced,n in [(False,0),(False,8),(True,0),(True,1),(True,8),(True,15)]:
  for road in [0,255]:
   for obj in [0,255]:
    out=[]
    for candidate in [False,True]:
     for addr,b in images:write(addr,b)
     write(code,bytes(native));write(sy['_terrain_select'],blobs[int(forced)])
     if candidate:
      write(code+0xcdbe,bytes.fromhex('4ef9')+struct.pack('>I',sy['_terrain_select']))
      write(code+0xc1b6,bytes.fromhex('4eb9')+struct.pack('>I',sy['_terrain_selected_hook'])+bytes.fromhex('4e71'))
     ok(u.uc_ctl(h,0x4000000a));reg(17,0x2010)
     for k in range(1,17):reg(k,0)
     reg(5,a4);reg(6,0x4e000);reg(8,sp);pack(sy['_time_scalar_fields'],'H',n);pack(a4-0x16b6,'BB',road,obj);pack(sy['_terrain_continuing'],'H',1)
     pack(a4-0x6bb8,'6h',0,16384,0,16384,0,16384)
     ok(u.uc_emu_start(h,code+0xcdbe,stop,1000000,1000000));assert reg(18)==stop and reg(8)==sp
     out.append((read(a4-32768,32768),[reg(k) for k in range(1,17)]))
    assert out[0][0]==out[1][0],(forced,n,road,obj,[(hex(i+32768),x,y) for i,(x,y) in enumerate(zip(out[0][0],out[1][0])) if x!=y][:35])
    changes=[k+1 for k,(x,y) in enumerate(zip(out[0][1],out[1][1])) if x!=y];volatile.update(changes)
    assert not set(changes)-{1,2,9,10,11},(forced,n,road,obj,changes)
    count+=1
 report=dict(passed=True,cases=count,volatile_register_differences=sorted(volatile),scope='Pristine native CDBE-to-CDF6 terrain, collision and contact execution versus assembled selector and installed road-index hook on captured game memory. All 32KB A4-relative data globals and callee-saved registers agree for all road/object flag combinations in zero/eight/forced-native modes. Volatile-register differences are reported; variable-step fallback side effects remain separate.')
 Path('tmp/c4-terrain-native-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
