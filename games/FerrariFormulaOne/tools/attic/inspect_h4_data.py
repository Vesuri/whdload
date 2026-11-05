exec(open('tmp/dev/tools/inspect_h4_native.py').read().split('text=[]')[0])
for x in [0x32cd3,0x2178c,0x216cc,0x1c22c]:print(hex(x),mem[x:x+80].hex(),repr(mem[x:x+80]))
for a,b in [(0x23288,0x23490),(0x24200,0x243cc)]:
 for i in c.disasm(mem[a:b],a):print(f'{i.address:06x}: {i.mnemonic} {i.op_str}')
