"""Read experimental weather-cycle ownership through the installed forecast hook."""
import struct

FIELDS=(('active',8,2),('owned',10,2),('message',12,2),('palette',14,2),
        ('message_ptr',16,4),('message_phase',20,4),('clock',24,4),
        ('trials',28,4),('forecasts',32,4),('starts',36,4),('expiries',40,4),
        ('messages',44,4),('palettes',48,4),('forecast_clock',52,4),
        ('start_clock',56,4),('expiry_clock',60,4),('duration',64,4),
        ('seed_before',68,2),('seed_after',70,2))
NATIVE=(('forecast_deadline',0x4bc,4),('active_deadline',0x4b8,4),
        ('forecast_flag',0x4c0,2),('transition',0x4c6,2),('rng',0x62,2),
        ('effects',0x4cc,2),('track',0x118,2),('loop',0x5e,4),
        ('message_deadline',0x64,4))


def locate(chip,code,game,base):
    if chip[game+0xdd0e:game+0xdd10]!=bytes.fromhex('4ef9'):
        return None
    entry=struct.unpack_from('>I',chip,game+0xdd10)[0]-base
    assert 0<=entry<len(code) and code[entry:entry+2]==bytes.fromhex('2f00')
    tag=code.find(b'PDWCYC01',entry,entry+4096)
    assert tag>=0 and code.find(b'PDWCYC01',tag+1,entry+4096)<0
    assert tag+72<=len(code)
    return base+tag


def snapshot(root,final=False):
    prefix='final-' if final else ''
    chip=(root/(prefix+'chip.bin')).read_bytes()
    code=(root/(prefix+'code.bin')).read_bytes()
    game=int((root/'game-base.txt').read_text(),0)
    base=int((root/'dump-base.txt').read_text(),0)
    address=locate(chip,code,game,base)
    assert address is not None
    result={name:struct.unpack_from('>H' if width==2 else '>I',code,address-base+off)[0]
            for name,off,width in FIELDS}
    result.update({name:struct.unpack_from('>H' if width==2 else '>I',chip,game+0xa6e+off)[0]
                   for name,off,width in NATIVE})
    return result


def probe_command(address,game,off):
    values=[f'*(unsigned {"short" if width==2 else "int"}*){address+i:#x}' for _,i,width in FIELDS]
    values += [f'*(unsigned {"short" if width==2 else "int"}*){game+0xa6e+i:#x}' for _,i,width in NATIVE]
    return ('printf "PDWCYCLE_EVENT %d '+hex(off)+' '+' '.join(['%u']*len(values))+
            '\\n", $pd_field, '+', '.join(values)+'\n')


def parse_values(text):
    values=list(map(int,text.split()))
    names=[name for name,_,_ in (*FIELDS,*NATIVE)]
    assert len(values)==len(names)
    return dict(zip(names,values))
