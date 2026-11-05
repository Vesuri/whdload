# Reuse the private 68000 loader/assembler, without its main traffic loops.
from pathlib import Path
exec(Path('tools/check_p1_micro.py').read_text().split('cases=0')[0].replace("root/'traffic-p1-before.s'", "root/'c5-traffic-before.s'"))
from game_image import hunks
native=hunks()[0]['data'];write(0x30000,native[0xd1c2:0xd29e]+b'\x4e\x75');write(0x38000,native[0x2950:0x295e]);write(a4-32604,bytes.fromhex('4ef9')+struct.pack('>I',0x38000))
patched=bytearray(native[0xd1c2:0xd29e]+b'\x4e\x75');patched[:6]=b'\x4e\xb9'+struct.pack('>I',syms[1]['_traffic_pose']);write(0x31000,bytes(patched));pack(syms[1]['_traffic_world_return'],'I',0x123456)
frame=0x90000;actor=0xa0000;cur=0xb0000;nxt=0xc0000
write(stop,bytes.fromhex('40f9000f0000'));rng=random.Random(200);cases=0
for i in range(20000):
 phase=rng.choice([0,1,165,199,200,32767,-32768,rng.randint(-32768,32767)])
 record_bytes=bytes(rng.randrange(256) for _ in range(46));actor_bytes=bytes(rng.randrange(256) for _ in range(44));cur_bytes=bytes(rng.randrange(256) for _ in range(20));next_bytes=bytes(rng.randrange(256) for _ in range(20));results=[]
 if i%3==0:
  record_bytes=bytearray(record_bytes);cur_bytes=bytearray(cur_bytes);next_bytes=bytearray(next_bytes)
  for j,(buf,offset) in enumerate([(record_bytes,28),(record_bytes,30),(record_bytes,32),(next_bytes,12),(cur_bytes,12),(next_bytes,16),(cur_bytes,16)]):
   if (i//3)%128 & (1<<j):buf[offset:offset+2]=b'\x00\x00'
  record_bytes,cur_bytes,next_bytes=map(bytes,[record_bytes,cur_bytes,next_bytes])
 for entry in [syms[0]['_traffic_pose_values'],syms[1]['_traffic_pose_values']]:
  write(record,record_bytes);write(actor,actor_bytes);write(cur,cur_bytes);write(nxt,next_bytes);pack(frame-8,'II',actor,nxt);pack(frame+8,'I',record);pack(frame+4,'I',0x123456 if i%2 else 0x654321)
  reg(17,0x2000);reg(4,cur);reg(5,a4);reg(6,frame);reg(13,phase&65535);reg(8,sp);pack(sp,'I',stop)
  ok(u.uc_emu_start(h,entry,stop,1000000,1000));assert reg(8)==sp+4
  ok(u.uc_emu_start(h,stop,stop+6,1000000,1))
  results.append((read(0xf0000,2),read(actor,44),read(record,46),reg(16)&65535,reg(3),reg(9),read(cur,20),read(nxt,20)))
 assert results[0]==results[1],(i,phase,results)
 cases+=1
report=dict(passed=True,cases=cases,scope='Previous production pose helper vs zero shortcuts: signed-word inputs, explicit zero masks, DIVS overflow, actor/record/route bytes, pitch, roll, final D0 and materialized CCR.')
(root/'c5-pose-zero-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
