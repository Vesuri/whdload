# Reuse the private 68000 loader/assembler, without its main traffic loops.
from pathlib import Path
exec(Path('tools/check_p1_micro.py').read_text().split('cases=0')[0])
from game_image import hunks
native=hunks()[0]['data'];write(0x30000,native[0xd1c2:0xd29e]+b'\x4e\x75');write(0x38000,native[0x2950:0x295e]);write(a4-32604,bytes.fromhex('4ef9')+struct.pack('>I',0x38000))
patched=bytearray(native[0xd1c2:0xd29e]+b'\x4e\x75');patched[:6]=b'\x4e\xb9'+struct.pack('>I',syms[1]['_traffic_pose']);write(0x31000,bytes(patched));pack(syms[1]['_traffic_world_return'],'I',0x123456)
frame=0x90000;actor=0xa0000;cur=0xb0000;nxt=0xc0000
rng=random.Random(200);cases=0
for i in range(20000):
 phase=rng.choice([0,1,165,199,200,32767,-32768,rng.randint(-32768,32767)])
 record_bytes=bytes(rng.randrange(256) for _ in range(46));actor_bytes=bytes(rng.randrange(256) for _ in range(44));cur_bytes=bytes(rng.randrange(256) for _ in range(20));next_bytes=bytes(rng.randrange(256) for _ in range(20));results=[]
 for entry in [0x30000,0x31000]:
  write(record,record_bytes);write(actor,actor_bytes);write(cur,cur_bytes);write(nxt,next_bytes);pack(frame-8,'II',actor,nxt);pack(frame+8,'I',record);pack(frame+4,'I',0x123456 if i%2 else 0x654321)
  reg(17,0x2000);reg(4,cur);reg(5,a4);reg(6,frame);reg(13,phase&65535);reg(8,sp);pack(sp,'I',stop)
  ok(u.uc_emu_start(h,entry,stop,1000000,1000));assert reg(8)==sp+4
  results.append((read(actor,44),read(record,46),reg(16)&65535,reg(3),reg(9),read(cur,20),read(nxt,20)))
 assert results[0]==results[1],(i,phase,results)
 cases+=1
report=dict(passed=True,cases=cases,scope='Actual pristine D1C2..D29E plus 2950 versus inlined traffic hook. Patched hook and native non-world fallback, all signed-word inputs, DIVS overflow, all record/actor/route bytes, pitch, roll and final D0.')
(root/'p1-pose.json').write_text(json.dumps(report,indent=2)+'\n');print(report);ok(u.uc_close(h))
