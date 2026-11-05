from unicorn_b import *
for filename in ('Gunship','GunshipNTSC'):
 blob=bytes(BinFmt().load_image(str(build/'release'/f'{filename}.Slave')).get_segments()[0].get_data())
 listing=(build/'release'/f'{filename}.lst').read_text(encoding='latin1')
 def a(n):return base+int(re.search(r'^([0-9A-F]{8}) '+n+r'$',listing,re.M)[1],16)
 for flags in (0,1,3,7,15,143):
  for enabled in (0,1):
   c=CPU();c.put(base,blob);c.put(a('_resload'),struct.pack('>I',0x500000));c.put(0x500034,b'\x4e\x75')
   c.put(a('_cpu_flags'),struct.pack('>I',flags));c.put(a('_custom1'),struct.pack('>I',enabled))
   c.call(a('_bootdos'),a('_bootdos')+0x20)
   assert int.from_bytes(c.get(a('_custom1'),4),'big')==(enabled if flags&2 else 0)
   c.close()
 print(filename,'master option off preserved; 68000/010 disabled; 020/030/040/060 enabled')
