from pathlib import Path
exec(Path('tools/check_native_engine_model.py').read_text().split('results=[]')[0])
subprocess.run([os.environ['VASM'],'-m68000','-devpac','-Fbin','-o','tmp/p4-power-table.bin','tmp/p4-power-table.s'],check=True,stdout=subprocess.DEVNULL)
b=Path('tmp/p4-power-table.bin').read_bytes();assert len(b)==8192
sp=0x4fff00;stop=0x490000;overflow=0;cases=0
def native(x,y,z):
 reg(17,0x2000);reg(8,sp);pack(sp,'Ihhh',stop,x,y,z)
 ok(u.uc_emu_start(h,codebase+0x2950,stop,1000000,20));assert reg(18)==stop
 return reg(9)
try:
 for k,(num,den) in enumerate([(7,800),(9,750),(10,600),(10,450)]):
  for byte in range(256):
   th=byte if byte<128 else byte-256;first=native(th,450,100)&65535;sf=first if first<32768 else first-65536;result=native(sf,den,num)
   table,tf,pad=struct.unpack_from('>IHH',b,(k*256+byte)*8)
   assert (table,tf,pad)==(result,first,0),(k,th,hex(table),hex(result),tf,first)
   q=abs(sf*den)//num*(-1 if sf<0 else 1);overflow+=not(-32768<=q<=32767);cases+=1
 report=dict(passed=True,cases=cases,division_overflows=overflow,scope='All signed throttle bytes and four immutable game ratios; exact full native D0 including DIVS overflow and intermediate D4 word. Lookup not integrated.')
 Path('tmp/p4-power-table-check.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
finally:ok(u.uc_close(h))
