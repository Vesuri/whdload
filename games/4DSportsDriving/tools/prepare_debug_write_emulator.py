#!/usr/bin/env python3
"""Create a separate private profiler build with bounded stopped-target writes."""
from pathlib import Path
import subprocess,hashlib,json
src=Path('tmp/profiler-fsuae');dst=Path('tmp/contact-write-fsuae');assert not dst.exists()
subprocess.run(['cp','-cRp',str(src),str(dst)],check=True)
p=dst/'src/barto_gdbserver.cpp';s=p.read_text();old=s
marker='\tstatic std::string get_registers() {'
helpers='''
    // Private contact diagnostics: writes are legal only while CPU is stopped.
    static bool contact_hex(const std::string& text, uint32_t& value) {
        if(text.empty() || text.size() > 8) return false;
        value = 0;
        for(unsigned char c : text) {
            unsigned n;
            if(c >= '0' && c <= '9') n = c - '0';
            else if(c >= 'a' && c <= 'f') n = c - 'a' + 10;
            else if(c >= 'A' && c <= 'F') n = c - 'A' + 10;
            else return false;
            value = (value << 4) | n;
        }
        return true;
    }
    static bool contact_ram(uaecptr address, uint32_t length) {
        if(length > 256 || address > UINT32_MAX - length) return false;
        for(uint32_t i = 0; i < length; ++i)
            if(!debug_safe_addr(address+i, 1) || !(get_mem_bank(address+i).flags & ABFLAG_RAM)) return false;
        return true;
    }
    static bool contact_write_memory(const std::string& request) {
        auto comma=request.find(','), colon=request.find(':');
        uint32_t address, length;
        if(debugger_state != state::debugging || comma==std::string::npos || colon==std::string::npos || colon<=comma ||
           !contact_hex(request.substr(1,comma-1),address) || !contact_hex(request.substr(comma+1,colon-comma-1),length) ||
           length>256 || request.size()-colon-1 != 2*length || !contact_ram(address,length)) return false;
        std::vector<uint32_t> bytes(length);
        for(uint32_t i=0;i<length;++i)
            if(!contact_hex(request.substr(colon+1+2*i,2),bytes[i])) return false;
        for(uint32_t i=0;i<length;++i) get_mem_bank(address+i).bput(address+i,bytes[i]);
        cpu_invalidate_cache(address,length);
        return true;
    }
    static bool contact_write_register(const std::string& request) {
        auto eq=request.find('='); uint32_t index,value;
        if(debugger_state != state::debugging || eq==std::string::npos || request.size()-eq-1!=8 ||
           !contact_hex(request.substr(1,eq-1),index) || !contact_hex(request.substr(eq+1),value)) return false;
        if(index<=D7) m68k_dreg(regs,index-D0)=value;
        else if(index>=A0 && index<=A7) m68k_areg(regs,index-A0)=value;
        else if(index==PC) {
            if((value&1) || !contact_ram(value,2)) return false;
            m68k_setpc_normal(value);
            fill_prefetch();
        } else return false; // SR/FPU writes deliberately unsupported.
        return true;
    }
'''
assert s.count(marker)==1;s=s.replace(marker,helpers+marker)
marker="} else if(request[0] == 'g') { // get registers"
assert s.count(marker)==1
s=s.replace(marker,"} else if(request[0] == 'M') {\n                                    response += contact_write_memory(request) ? \"OK\" : \"E01\";\n                                } else if(request[0] == 'P') {\n                                    response += contact_write_register(request) ? \"OK\" : \"E01\";\n                                "+marker)
p.write_text(s)
import difflib
Path('tools/contact-debug-writes.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/src/barto_gdbserver.cpp',tofile='b/src/barto_gdbserver.cpp')))
Path('tmp/build/contact-write-parent.json').write_text(json.dumps({'parent_binary_sha256':hashlib.sha256((src/'fs-uae').read_bytes()).hexdigest(),'parent_source_sha256':hashlib.sha256(old.encode()).hexdigest(),'scope':'Private bounded debugger RAM/PC writes; no global emulator or game changes.'},indent=2)+'\n')
