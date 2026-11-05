__file__=__file__.replace('debug_effect.py','test_runtime_batch_c.py')
s=open(__file__).read();exec(s.split('runs=[];yields=0')[0])
setup(50);c.put(h[6]+0x42f7,bytes([120]));c.put(h[0]+0xc6d0,bytes(90))
print('pointers',hex(long(ptr('CONSUMER')+68)),hex(ptr('EFFECTS')),hex(long(ptr('CONSUMER')+72)),hex(h[6]+0x42f7),flush=True)
for n in range(1,36):
 publish(n,0);result=pump()
 print(n,result,c.get(h[6]+0x42f7,1).hex(),c.get(h[0]+0xba08,4).hex(),c.get(h[0]+0xc6d0,18).hex(),flush=True)
