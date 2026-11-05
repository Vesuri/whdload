# Loaded inside LLDB. Find the live slow bank by a verified guest-memory signature.
import lldb
_cache={}

def poke(debugger, command, result, _):
    address, hexdata, signature, guest_signature = command.split()
    addresses=[int(a,0) for a in address.split(",")];payloads=[bytes.fromhex(b) for b in hexdata.split(",")];assert len(addresses)==len(payloads);guest_signature=int(guest_signature,0)
    process=debugger.GetSelectedTarget().GetProcess()
    needle=bytes.fromhex(signature);regions=process.GetMemoryRegions();found=[]
    cached=_cache.get(signature)
    if cached is not None:
        error=lldb.SBError()
        assert process.ReadMemory(cached,len(needle),error)==needle
        found=[cached]
    for i in range(0 if found else regions.GetSize()):
        r=lldb.SBMemoryRegionInfo();regions.GetMemoryRegionAtIndex(i,r)
        if not r.IsReadable() or not r.IsWritable():continue
        lo,hi=r.GetRegionBase(),r.GetRegionEnd()
        if hi-lo>512*1024*1024:continue
        for start in range(lo,hi,4*1024*1024):
            error=lldb.SBError();data=process.ReadMemory(start,min(4*1024*1024+len(needle),hi-start),error)
            if not error.Success():continue
            pos=data.find(needle)
            if pos>=0:found.append(start+pos)
    if len(found)!=1:raise RuntimeError('signature matches '+str(found))
    _cache[signature]=found[0]
    for address,data in zip(addresses,payloads):
        host=found[0]+address-guest_signature;error=lldb.SBError()
        assert process.WriteMemory(host,data,error)==len(data),str(error)
        assert process.ReadMemory(host,len(data),error)==data
    result.AppendMessage('WROTE '+','.join(hex(a) for a in addresses)+' '+hexdata+' VERIFIED')

def __lldb_init_module(debugger, _):
    debugger.HandleCommand('command script add -f host_poke.poke hd-poke')
