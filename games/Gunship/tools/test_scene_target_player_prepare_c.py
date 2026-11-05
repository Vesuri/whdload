"""Private-player preparation ABI and atomic signature rejection."""
__file__=__file__.replace('test_scene_target_player_prepare_c.py','test_scene_target_c.py')
exec(open(__file__).read().split('cases=0;counts=set();nonempty=0')[0])
c.put(0x200000,mem)
areas=[(scene,sym('SCT_SELECTION')+168),(target,sym('WT_SIZE')),(collector,sym('WTC_CODE_SIZE'))]
args={1:h[0],2:h[4],3:h[6],4:scene,5:target,6:collector,7:0x140000}
rejects=0
for start in (0x61c0,0x61d2,0xa4f6):
 for delta in range(6):
  address=h[0]+start+delta;saved=c.get(address,1);c.put(address,bytes([saved[0]^1]))
  for address2,length in areas:c.put(address2,b'Z'*length)
  assert call(addr('scene_target_player_prepare'),args)==0xffffffff
  assert all(c.get(address2,length)==b'Z'*length for address2,length in areas)
  c.put(address,saved);rejects+=1
regs={r:0x1100+r for r in range(1,17) if r!=8};regs.update(args)
assert call(addr('scene_target_player_prepare'),regs)==0
assert all(c.rr(r)==v for r,v in regs.items() if r!=9)
assert int.from_bytes(c.get(scene+0x61c2-sym('SCENE_START'),4),'big')==0x140000
assert int.from_bytes(c.get(scene+0x61d4-sym('SCENE_START'),4),'big')==0x140002
assert int.from_bytes(c.get(collector+0xa4f8-0xa450,4),'big')==0x14001a
print(dict(status='passed',atomic_signature_rejections=rejects,registers_preserved=True,private_bindings=3));c.close()
