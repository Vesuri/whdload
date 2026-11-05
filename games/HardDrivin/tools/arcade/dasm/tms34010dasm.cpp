// Linear TMS34010 disassembly of a raw little-endian image with MAME's disassembler.
// Usage: tms34010dasm IMAGE BASE_BITADDR [START_BITADDR END_BITADDR]
#include "emu.h"
#include "34010dsm.h"
#include <cstdio>
#include <sstream>
#include <vector>
struct buf : util::disasm_interface::data_buffer {
	std::vector<uint8_t> d; uint32_t base;
	u16 w(offs_t pc) const { size_t o=(pc-base)>>3; return o+1<d.size() ? d[o]|(d[o+1]<<8) : 0; }
	u8 r8(offs_t pc) const override { size_t o=(pc-base)>>3; return o<d.size()?d[o]:0; }
	u16 r16(offs_t pc) const override { return w(pc); }
	u32 r32(offs_t pc) const override { return w(pc)|(u32(w(pc+16))<<16); }
	u64 r64(offs_t pc) const override { return r32(pc)|(u64(r32(pc+32))<<32); }
};
int main(int argc,char**argv) {
	buf b; FILE*f=fopen(argv[1],"rb"); int c; while((c=fgetc(f))!=EOF) b.d.push_back(c); fclose(f);
	b.base=strtoul(argv[2],0,16);
	uint32_t pc=argc>3?strtoul(argv[3],0,16):b.base, end=argc>4?strtoul(argv[4],0,16):b.base+b.d.size()*8;
	tms34010_disassembler dis(false);
	while(pc<end) {
		std::ostringstream s; uint32_t n=dis.disassemble(s,pc,b,b)&0xffff;
		printf("%08X:",pc); for(uint32_t i=0;i<n;i+=16) printf(" %04X",b.w(pc+i)); for(uint32_t i=n;i<64;i+=16) printf("     ");
		printf("  %s\n",s.str().c_str()); pc+=n;
	}
}
