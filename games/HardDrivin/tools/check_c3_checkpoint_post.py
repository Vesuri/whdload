from pathlib import Path
import ctypes as C,json,os,re,struct,subprocess,sys
exec(Path('tools/check_p2_micro.py').read_text().split('for addr,name,path in ')[0])
ok(u.uc_mem_map(h,0,0x10000,7));ok(u.uc_mem_map(h,0x50000,0xfb0000,7))
sys.path.insert(0,'tools');from game_image import hunks
root=Path('tmp/prof/c3-checkpoint-post-slow');meta=json.loads((root/'metadata.json').read_text());lay=meta['layout'];a4=lay['a4'];code=lay['code_base'];sp=0x4f000;stop=0x41000
images=[(addr,(root/f'timing-state-{name}.bin').read_bytes()) for name,addr in [('chip',0),('slow',0xc00000)]]
listing=Path('tmp/build/c3-checkpoint-post.lst').read_text(encoding='latin1');sy={n:int(v,16) for n,v in re.findall(r'^(_\w+)\s+00:([0-9A-F]+)',listing,re.M)};base=lay['published']-sy['_code_start'];sy={k:base+v for k,v in sy.items()}
hs=hunks();native=bytearray(hs[0]['data']);bases=[r['base'] for r in lay['regions']]
for off,dest in hs[0]['relocs']:struct.pack_into('>I',native,off,struct.unpack_from('>I',native,off)[0]+bases[dest])
body=Path('src/HardDrivinCheckpoint.s').read_text().replace('_checkpoint_post','_private_checkpoint_post');blobs=[]
for forced in [False,True]:
 stem=Path('tmp/c3-checkpoint-test-'+str(forced));symbols='\n'.join('%s equ $%x'%(k,v) for k,v in sy.items() if k!='_private_checkpoint_post');stem.with_suffix('.s').write_text(' org $%x\n'%sy['_private_checkpoint_post']+('VERIFY_DISPATCH_NATIVE equ 1\n' if forced else '')+symbols+'\n'+body);subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o',str(stem.with_suffix('.bin')),str(stem.with_suffix('.s'))],check=True,stdout=subprocess.DEVNULL);blobs.append(stem.with_suffix('.bin').read_bytes())
# Award routines are stubs: real C022 and terrain-selection hook still execute.
for a,b in images:write(a,b)
roadbase=struct.unpack('>I',read(a4-0x66ae,4))[0]
count=0;calls=0;selected_changes=0
try:
 for forced in [False,True]:
  for n in [0,1,8,15]:
   for race in [0,255]:
    for wrong in [0,255]:
     for chosen,reverse in [(0,False),(0,True),(1,False),(1,True)]:
      for flags in [0,0x1000,0x2000,0x3000]:
       for a,b in images:write(a,b)
       write(code,bytes(native));write(sy['_private_checkpoint_post'],blobs[int(forced)])
       write(code+0xc1b6,bytes.fromhex('4eb9')+struct.pack('>I',sy['_terrain_selected_hook'])+bytes.fromhex('4e71'))
       for off,ptr in [(0x92c0,0x42000),(0x936a,0x42004)]:write(code+off,bytes.fromhex('52b9')+struct.pack('>I',ptr)+bytes.fromhex('4e75'))
       write(stop,bytes.fromhex('40f900042008'));write(0x42000,bytes(16));ok(u.uc_ctl(h,0x4000000a))
       reg(17,0x2010)
       for k in range(1,17):reg(k,0x10000000+k)
       reg(5,a4);reg(8,sp);pack(sp,'I',stop);pack(sy['_time_scalar_fields'],'H',n);pack(sy['_terrain_selected'],'H',0xcafe)
       pack(a4-0x522c,'B',race);pack(a4-0x16d0,'B',wrong);pack(a4-0x66b0,'B',1);pack(a4-0x671c,'I',roadbase+60*20)
       record=read(roadbase+(60+chosen)*20,12);v=struct.unpack('>6h',record)
       for off,value in zip([0x98f6,0x98f8,0x98fa],[(v[0]+v[3])//2,(v[1]+v[4])//2,(v[2]+v[5])//2]):pack(a4+off-65536,'h',value)
       pack(roadbase+60*20+18,'H',flags if chosen==0 else 0);pack(roadbase+61*20+18,'H',flags if chosen==1 else 0)
       pack(a4-0x6bb8,'6h',16339 if reverse else -16339,-1214 if reverse else 1214,0,16384,0,16384)
       before=read(a4-32768,32768);regs=[reg(k) for k in range(1,17)]
       ok(u.uc_emu_start(h,sy['_private_checkpoint_post'],stop+6,1000000,1000000));assert reg(18)==stop+6 and reg(8)==sp+4
       assert read(a4-32768,32768)==before,(forced,n,race,wrong,chosen,flags,'state')
       actual=[reg(k) for k in range(1,17)];assert actual[:7]+actual[8:]==regs[:7]+regs[8:]
       enabled=not forced and n not in [0,8] and race and not reverse and flags
       expected=(1,0) if enabled and flags&0x1000 else (0,1) if enabled and flags&0x2000 else (0,0)
       result=struct.unpack('>2I',read(0x42000,8));assert result==expected,(forced,n,race,wrong,chosen,flags,result,expected)
       if forced or n in [0,8] or not race or not flags:assert struct.unpack('>H',read(0x42008,2))[0]&16
       calls+=sum(result);selected_changes+=read(sy['_terrain_selected'],2)!=bytes.fromhex('cafe');assert read(sy['_terrain_selected'],2)==bytes.fromhex('cafe');count+=1
 report=dict(passed=True,cases=count,award_calls=calls,selected_word_changes=selected_changes,scope='Actual 68000 private helper with native C022/selection hook; award bodies stubbed. Both candidate records, flags, race gate, forward/reverse physical orientations, either stale wrong-way flag, zero/eight/forced-native bypasses. All 32KB game data and registers/stack preserved; bypass X checked. Does not validate native award side effects, arbitrary geometry or whole courses.')
 Path('tmp/c3-checkpoint-post-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
