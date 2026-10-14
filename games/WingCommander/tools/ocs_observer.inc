// P13A4: read-only host observations on the cycle-exact 68000 interpreter.
// No guest writes, custom register reads, cycle charges or interior debugger stops.
static FILE* ocs_log = nullptr;
static unsigned ocs_h0, ocs_h1, ocs_mode, ocs_field;
static bool ocs_active = false;
static unsigned ocs_buffers[2], ocs_plane;
static int ocs_seen = -1;
static uae_u64 ocs_begin_cycles, ocs_cpu[4];
static std::vector<unsigned char> ocs_previous;
struct ocs_scope { unsigned off, sp, ret; uae_u64 start; };
static std::vector<ocs_scope> ocs_scopes;

static void ocs_memory() {
    unsigned header = get_long_debug(get_long_debug(4)+322);
    unsigned free_chip=0, free_fast=0, n=0;
    while (get_long_debug(header)) {
        if (++n>16) abort();
        unsigned attrs=get_word_debug(header+14), free=get_long_debug(header+28);
        if (attrs&2) free_chip+=free;
        else if (attrs&4) free_fast+=free;
        header=get_long_debug(header);
    }
    fprintf(ocs_log,"M %llu %u %u\n",(unsigned long long)get_cycles(),free_chip,free_fast);
}
void wc_ocs_begin(unsigned h0,unsigned h1,unsigned mode,const char* path) {
    if (ocs_log || mode>1 || h0<0x200000 || h1<0x200000) abort();
    ocs_log=fopen(path,"wx"); if (!ocs_log) abort();
    ocs_h0=h0; ocs_h1=h1; ocs_mode=mode; ocs_field=0;
    ocs_begin_cycles=get_cycles(); ocs_active=mode!=0;
    ocs_previous.clear(); ocs_scopes.clear(); ocs_seen=-1;
    for (auto& c:ocs_cpu) c=0;
    ocs_buffers[0]=get_long_debug(h0+0x331c0);
    ocs_buffers[1]=get_long_debug(h0+0x331c4);
    ocs_plane=get_word_debug(h0+0x331d2);
    fprintf(ocs_log,"B %llu %u %u %u %u %u %u\n",(unsigned long long)get_cycles(),
        baseclock,CYCLE_UNIT,cpucycleunit,get_word_debug(h1+0x88da),
        get_word_debug(h1+0x88de),get_long_debug(h1+0x77fe));
    ocs_memory(); fflush(ocs_log);
}
void wc_ocs_field(bool end) {
    if (!ocs_log) abort();
    ++ocs_field;
    fprintf(ocs_log,"F %llu %u %u %u %u\n",(unsigned long long)get_cycles(),ocs_field,
        get_word_debug(ocs_h1+0x88da),get_word_debug(ocs_h1+0x88de),get_long_debug(ocs_h1+0x77fe));
    ocs_memory(); ocs_seen=-1;
    if (end) {
        ocs_active=false;
        fprintf(ocs_log,"E %llu %llu %llu %llu %llu\n",(unsigned long long)get_cycles(),
            (unsigned long long)ocs_cpu[0],(unsigned long long)ocs_cpu[1],
            (unsigned long long)ocs_cpu[2],(unsigned long long)ocs_cpu[3]);
        fclose(ocs_log); ocs_log=nullptr;
    } else fflush(ocs_log);
}
// Called at actual bitplane fetches, independently of game PCs/publication state.
void wc_ocs_fetch(unsigned p,unsigned nr) {
    if (!ocs_active || nr) return;
    int index=-1;
    for (int n=0;n<2;++n) if (p>=ocs_buffers[n] && p<ocs_buffers[n]+ocs_plane) index=n;
    if (index<0) return;
    if (index!=ocs_seen) {
        fprintf(ocs_log,"D %llu %u %d %x\n",(unsigned long long)get_cycles(),ocs_field,index,p);
        ocs_seen=index;
    }
}
static void wc_ocs_pc(unsigned pc) {
    if (!ocs_active) return;
    unsigned off=pc-ocs_h0, sp=m68k_areg(regs,7);
    // Saved return address + restored SP distinguishes nested and interrupt calls.
    for (size_t n=0;n<ocs_scopes.size();++n) {
        const auto s=ocs_scopes[n];
        if (pc!=s.ret || sp!=s.sp+4) continue;
        fprintf(ocs_log,"R %llu %x %llu %x\n",(unsigned long long)get_cycles(),s.off,
            (unsigned long long)s.start,regs.regs[0]);
        ocs_scopes.erase(ocs_scopes.begin()+n); break;
    }
    const unsigned scopes[]={0x2be,0x2e6,0xb80,0x32990,0x3407e,0x340ba,0x6fa,0xc748};
    for (unsigned entry:scopes) if (off==entry) {
        if (sp<0x100 || sp>0x600000-4 || ocs_scopes.size()>32) abort();
        ocs_scopes.push_back({off,sp,get_long_debug(sp),get_cycles()});
        fprintf(ocs_log,"S %llu %x\n",(unsigned long long)get_cycles(),off);
    }
    const unsigned events[]={0x2dc,0x3260a,0x32626,0x3262a,0x3293a,0x32944,
        0x329de,0x329e4,0x32a0a,0x32a26,0x32a4a,0x32dba,0x32e02,0x33aa8,
        0x9618,0x33b98,0x33c88};
    for (unsigned entry:events) if (off==entry) {
        fprintf(ocs_log,"P %llu %x %x %x %u\n",(unsigned long long)get_cycles(),off,
            regs.regs[0],regs.regs[9],get_word_debug(ocs_h0+0x331d8));
        if (off==0x33b98 || off==0x33c88) ocs_memory();
    }
    if (off==0x32626) {
        unsigned w=get_word_debug(ocs_h0+0x324ac),h=get_word_debug(ocs_h0+0x324ae);
        unsigned source=get_long_debug(ocs_h0+0x324b0),size=w*h,changed=0,blocks=0;
        if (w!=320 || (h!=128 && h!=200) || source+size>0x80000) abort();
        std::vector<unsigned char> current(size);
        bool comparable=ocs_previous.size()==size, block=false;
        for(unsigned i=0;i<size;++i) {
            current[i]=get_byte_debug(source+i);
            if(comparable && current[i]!=ocs_previous[i]) { ++changed; block=true; }
            if((i&31)==31) { blocks+=block; block=false; }
        }
        fprintf(ocs_log,"C %llu %u %u %u %u\n",(unsigned long long)get_cycles(),size,comparable,changed,blocks);
        ocs_previous.swap(current);
    }
}
// Scope duration is inclusive; these instruction charges isolate actual CPU polls.
struct ocs_instruction {
    uae_u64 start=0; unsigned kind=0;
    explicit ocs_instruction(unsigned pc) {
        if (!ocs_active) return;
        start=get_cycles();
        unsigned off=pc-ocs_h0;
        if (off==0x3293e || off==0x32942) kind=1;
        else if (off>=0x32a66 && off<0x32dba) {
            unsigned op=get_word_debug(pc);
            if(op==0x0113 || op==0x66fc) kind=2;
        }
    }
    ~ocs_instruction() {
        if (start && ocs_active) ocs_cpu[kind]+=get_cycles()-start;
    }
};
