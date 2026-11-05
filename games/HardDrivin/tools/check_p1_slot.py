from pathlib import Path
exec(Path('tools/check_p1_micro.py').read_text().split('cases=0')[0])
ok(u.uc_mem_map(h,0x500000,0x1000000,7));sy=syms[1];table=0x100000;comp=0x500000;valid=0x900000
write(stop,bytes.fromhex('40f9000420004e71'));end=stop+8;bounds=0;pairs=0
for count in [0,1,12,713,65535]:
 extent=count*46;bitmap=bytearray(extent)
 for i in range(count):bitmap[i*46]=255
 if bitmap:write(valid,bytes(bitmap))
 pack(a4-0x50fc,'HI',count,table);pack(sy['_traffic_memory'],'IIII',comp,2*extent,extent,valid)
 offsets=[-2,0,1,2,44,45,46,extent-46,extent-2,extent-1,extent,extent+1]
 offsets += [rng.randrange(extent+46) for _ in range(200)]
 for off in offsets:
  for x in [0,16]:
   reg(17,0x2000+x);reg(1,table+off);reg(2,0xabcdef);reg(5,a4);reg(8,sp);reg(9,0x12345678);pack(sp,'I',stop)
   ok(u.uc_emu_start(h,sy['_traffic_slot'],end,1000000,1000))
   accepted=0<=off<extent and off%46==0
   assert reg(2)==(comp+off if accepted else 0),(count,off,reg(2))
   assert reg(9)==0x12345678 and reg(8)==sp+4 and read(0x42000,2)[1]&16==x
   bounds+=1
from game_image import hunks
native=hunks()[0]['data'];frame=0xd0000;actor=0xe0000
for i,(name,start,length) in enumerate([('speed',0xce8a,42),('phase',0xd36e,18),('collision',0xbc4c,6)]):
 original=0x30000+i*0x100;write(original,native[start:start+length]+b'\x4e\x75')
 for speed in range(256):
  for target,accel in [(0,1),(20,2),(127,3),(128,255),(255,127)]:
   initial=[rng.randrange(2**32) for _ in range(16)];initial[0]=record;initial[4]=a4;initial[5]=frame;initial[7]=sp
   states=[]
   for entry in [original,sy['_traffic_'+name]]:
    pack(a4-0x50fc,'HI',12,table);pack(sy['_traffic_memory'],'IIII',comp,1104,552,valid);pack(sy['_traffic_world_return'],'I',0x123456)
    write(record,bytes([0xa5])*46);pack(record+21,'BBB',accel,target,speed);write(actor,bytes([0x5a])*44);pack(frame+8,'I',record);pack(frame-8,'I',actor);pack(frame-14,'I',0);pack(frame+4,'I',0x333333)
    reg(17,0x2000|(speed&31))
    for k,v in enumerate(initial,1):reg(k,v)
    pack(sp,'I',stop);ok(u.uc_emu_start(h,entry,end,1000000,1000));states.append(([reg(k) for k in range(1,17)],read(record,46),read(actor,44),read(0x42000,2)))
   assert states[0]==states[1],(name,speed,target,accel,states)
   pairs+=1
r=dict(passed=True,boundary_alignment_and_X_cases=bounds,native_fallback_pairs=pairs);(root/'p1-slot.json').write_text(json.dumps(r,indent=2)+'\n');print(r);ok(u.uc_close(h))
