// P13A4/C2: read-only host observations on cycle-exact 68000/020 interpreters.
// No guest writes, custom register reads, cycle charges or interior debugger stops.
static FILE* ocs_log = nullptr;
static FILE* ocs_sources = nullptr;
// Optional C6 disjoint owned-code ranges: full adapter, changed adapter, leaves.
// Parsed once; host-only instruction charges, with no guest instrumentation.
static unsigned ocs_cost_ranges[6];
static uae_u64 ocs_cost[3];
static bool ocs_cost_started=false;
static unsigned ocs_h0, ocs_h1, ocs_mode, ocs_field;
static bool ocs_active = false;
static unsigned ocs_buffers[2], ocs_plane;
static int ocs_seen = -1;
static uae_u64 ocs_begin_cycles, ocs_cpu[4], ocs_dma_wait[2];
void wc_ocs_dma_wait(bool bitplane) { if(ocs_active) ++ocs_dma_wait[bitplane?1:0]; }
static std::vector<unsigned char> ocs_previous, ocs_expected;
static unsigned ocs_target, ocs_width, ocs_height;
// D3 optional addresses supplied from the pinned candidate symbol map. Record
// the installed queue's actual target at return, not the C5 ready+1 assumption.
static unsigned ocs_prediction_fields[3], ocs_queue_ret, ocs_queue_sp;
static unsigned ocs_queue_index, ocs_queue_estimate, ocs_queue_ready, ocs_queue_predicted;
static uae_u64 ocs_queue_cycles;
// C5: independent completed-image bytes checked at actual bitplane DMA reads.
static std::vector<unsigned char> ocs_reference[2], ocs_valid[2];
static unsigned ocs_fetch_good, ocs_fetch_bad, ocs_fetch_unknown;

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
    if(mode) { std::string sources=std::string(path)+".sources";
        ocs_sources=fopen(sources.c_str(),"wx"); if(!ocs_sources) abort(); }
    for(auto& v:ocs_prediction_fields) v=0;
    ocs_queue_ret=0;
    const char* prediction=getenv("WC_OCS_PREDICTION_FIELDS");
    if(prediction) {
        if(sscanf(prediction,"%x,%x,%x", &ocs_prediction_fields[0],
            &ocs_prediction_fields[1],&ocs_prediction_fields[2])!=3) abort();
        for(auto v:ocs_prediction_fields) if(v<0x200000 || v>0xa00000-4) abort();
    }
    ocs_h0=h0; ocs_h1=h1; ocs_mode=mode; ocs_field=0;
    ocs_begin_cycles=get_cycles(); ocs_active=mode!=0;
    for(auto& v:ocs_cost_ranges) v=0;
    const char* ranges=getenv("WC_OCS_COST_RANGES");
    if(ranges && sscanf(ranges,"%x,%x,%x,%x,%x,%x",&ocs_cost_ranges[0],&ocs_cost_ranges[1],
        &ocs_cost_ranges[2],&ocs_cost_ranges[3],&ocs_cost_ranges[4],&ocs_cost_ranges[5])!=6) abort();
    if(ranges) for(unsigned n=0;n<3;++n) {
        if(ocs_cost_ranges[2*n]<0x200000 || ocs_cost_ranges[2*n]>=ocs_cost_ranges[2*n+1] ||
           ocs_cost_ranges[2*n+1]>0xa00000) abort();
        for(unsigned j=0;j<n;++j) if(ocs_cost_ranges[2*n]<ocs_cost_ranges[2*j+1] &&
            ocs_cost_ranges[2*j]<ocs_cost_ranges[2*n+1]) abort();
    }
    for(auto& v:ocs_cost) v=0;
    ocs_cost_started=false;
    ocs_previous.clear(); ocs_expected.clear(); ocs_scopes.clear(); ocs_seen=-1;
    for(unsigned n=0;n<2;++n) { ocs_reference[n].clear(); ocs_valid[n].clear(); }
    ocs_fetch_good=ocs_fetch_bad=ocs_fetch_unknown=0;
    for (auto& c:ocs_cpu) c=0;
    for (auto& c:ocs_dma_wait) c=0;
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
    fprintf(ocs_log,"Y %u %u %u %u\n",ocs_field,ocs_fetch_good,ocs_fetch_bad,ocs_fetch_unknown);
    ocs_fetch_good=ocs_fetch_bad=ocs_fetch_unknown=0;
    ocs_memory(); ocs_seen=-1;
    if (end) {
        ocs_active=false;
        fprintf(ocs_log,"T %llu %llu\n",(unsigned long long)ocs_dma_wait[0],(unsigned long long)ocs_dma_wait[1]);
        fprintf(ocs_log,"E %llu %llu %llu %llu %llu\n",(unsigned long long)get_cycles(),
            (unsigned long long)ocs_cpu[0],(unsigned long long)ocs_cpu[1],
            (unsigned long long)ocs_cpu[2],(unsigned long long)ocs_cpu[3]);
        fclose(ocs_log); ocs_log=nullptr;
        if(ocs_sources) { fclose(ocs_sources); ocs_sources=nullptr; }
    } else fflush(ocs_log);
}
// Called at actual bitplane fetches, independently of game PCs/publication state.
void wc_ocs_fetch(unsigned p,unsigned nr) {
    if (!ocs_active) return;
    bool checked=false;
    for(unsigned n=0;n<2;++n) if(p>=ocs_buffers[n] && p+1<ocs_buffers[n]+ocs_reference[n].size()) {
        unsigned at=p-ocs_buffers[n];
        if(ocs_valid[n][at] && ocs_valid[n][at+1]) {
            unsigned expected=(ocs_reference[n][at]<<8)|ocs_reference[n][at+1];
            ++ocs_fetch_good; ocs_fetch_bad+=get_word_debug(p)!=expected; checked=true;
        }
    }
    if(!checked) ++ocs_fetch_unknown;
    if(nr) return;
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
    if(ocs_queue_ret && pc==ocs_queue_ret && sp==ocs_queue_sp+4) {
        unsigned target=get_long_debug(ocs_prediction_fields[0]);
        fprintf(ocs_log,"Q %llu %u %u\n",(unsigned long long)ocs_queue_cycles,ocs_queue_index,target);
        fprintf(ocs_log,"G %llu %u %u %u %u\n",(unsigned long long)get_cycles(),
            ocs_queue_estimate,target,ocs_queue_ready,ocs_queue_predicted);
        ocs_queue_ret=0;
    }
    // Saved return address + restored SP distinguishes nested and interrupt calls.
    for (size_t n=0;n<ocs_scopes.size();++n) {
        const auto s=ocs_scopes[n];
        if (pc!=s.ret || sp!=s.sp+4) continue;
        fprintf(ocs_log,"R %llu %x %llu %x\n",(unsigned long long)get_cycles(),s.off,
            (unsigned long long)s.start,regs.regs[0]);
        ocs_scopes.erase(ocs_scopes.begin()+n); break;
    }
    if(off==0x33442) {
        if(ocs_prediction_fields[0]) {
            if(ocs_queue_ret) abort();
            ocs_queue_ret=get_long_debug(sp); ocs_queue_sp=sp; ocs_queue_cycles=get_cycles();
            ocs_queue_index=get_word_debug(ocs_h0+0x331d8);
            ocs_queue_ready=get_long_debug(ocs_h1+0x77fe)+1;
            ocs_queue_estimate=get_long_debug(ocs_prediction_fields[1]);
            ocs_queue_predicted=get_word_debug(ocs_prediction_fields[2]);
        } else fprintf(ocs_log,"Q %llu %u %u\n",(unsigned long long)get_cycles(),
            get_word_debug(ocs_h0+0x331d8),get_long_debug(ocs_h1+0x77fe)+1);
    }
    const unsigned scopes[]={0x2be,0x2e6,0xb80,0x32990,0x3407e,0x340ba,0x6fa,0xc748};
    for (unsigned entry:scopes) if (off==entry) {
        if (sp<0x100 || sp>0xdc0000-4 || ocs_scopes.size()>32) abort();
        ocs_scopes.push_back({off,sp,get_long_debug(sp),get_cycles()});
        fprintf(ocs_log,"S %llu %x\n",(unsigned long long)get_cycles(),off);
    }
    const unsigned events[]={0x2dc,0x3260a,0x32626,0x3262a,0x3293a,0x32944,
        0x329de,0x329e4,0x32a0a,0x32a26,0x32a4a,0x32dba,0x32e02,0x33aa8,
        0x9618,0x33b98,0x33c88,0x32e06,0x3342e,0x33350,0x333ba,0x334bc,0x342c8};
    for (unsigned entry:events) if (off==entry) {
        fprintf(ocs_log,"P %llu %x %x %x %u\n",(unsigned long long)get_cycles(),off,
            regs.regs[0],regs.regs[9],get_word_debug(ocs_h0+0x331d8));
        if (off==0x33aa8) fprintf(ocs_log,"V %llu %u %u %u\n",(unsigned long long)get_cycles(),
            ocs_field,get_long_debug(ocs_h1+0x77fe),vpos);
        if (off==0x33b98 || off==0x33c88) ocs_memory();
    }
    if(off==0x33350 || off==0x333ba) {
        unsigned n=get_word_debug(ocs_h0+0x331d6);
        if(n<2) std::fill(ocs_valid[n].begin(),ocs_valid[n].end(),0);
    }
    if(off==0x32e06 && !ocs_expected.empty()) {
        unsigned bad=0,row=ocs_width/8,plane=row*(ocs_height+2);
        int target=-1; for(int n=0;n<2;++n) if(ocs_target==ocs_buffers[n]) target=n;
        if(target<0) abort();
        ocs_reference[target].assign(4*plane,0);ocs_valid[target].assign(4*plane,0);
        for(unsigned bit=0;bit<4;++bit) for(unsigned y=0;y<ocs_height-1;++y)
            for(unsigned x=0;x<row;++x) {
                unsigned char expected=0;
                for(unsigned k=0;k<8;++k) {
                    unsigned px=x*8+k, v=ocs_expected[y*ocs_width+px];
                    v=((px+y)&1)?(v&15):(v>>4);
                    if(y==1 && (px==1 || px==3 || px==9 || px==11)) v=0;
                    expected|=((v>>bit)&1)<<(7-k);
                }
                unsigned at=bit*plane+(y+2)*row+x;
                ocs_reference[target][at]=expected;ocs_valid[target][at]=1;
                bad+=get_byte_debug(ocs_target+at)!=expected;
            }
        fprintf(ocs_log,"X %llu %u %u\n",(unsigned long long)get_cycles(),bad,4*row*(ocs_height-1));
        ocs_expected.clear();
    }
    if(off==0x32e06 && ocs_cost_started) {
        fprintf(ocs_log,"K %llu %llu %llu %llu\n",(unsigned long long)get_cycles(),
            (unsigned long long)ocs_cost[0],(unsigned long long)ocs_cost[1],(unsigned long long)ocs_cost[2]);
        ocs_cost_started=false;
    }
    if (off==0x32626) {
        for(auto& v:ocs_cost) v=0;
        ocs_cost_started=true;
        unsigned w=get_word_debug(ocs_h0+0x324ac),h=get_word_debug(ocs_h0+0x324ae);
        unsigned source=get_long_debug(ocs_h0+0x324b0),size=w*h,changed=0,blocks=0;
        if (w!=320 || (h!=128 && h!=200) || !((source+size<=0x80000) || (source>=0x200000 && source+size<=0x600000))) abort();
        std::vector<unsigned char> current(size);
        bool comparable=ocs_previous.size()==size, block=false;
        for(unsigned i=0;i<size;++i) {
            current[i]=get_byte_debug(source+i);
            if(comparable && current[i]!=ocs_previous[i]) { ++changed; block=true; }
            if((i&31)==31) { blocks+=block; block=false; }
        }
        fprintf(ocs_log,"C %llu %u %u %u %u\n",(unsigned long long)get_cycles(),size,comparable,changed,blocks);
        if(fwrite(current.data(),1,current.size(),ocs_sources)!=current.size()) abort();
        ocs_expected=current; ocs_width=w; ocs_height=h;
        unsigned descriptor=get_long_debug(m68k_areg(regs,7));
        ocs_target=get_long_debug(descriptor+0x1c);
        unsigned hash=2166136261u;
        for(unsigned char byte:current) hash=(hash^byte)*16777619u;
        fprintf(ocs_log,"H %llu %u %u %u\n",(unsigned long long)get_cycles(),source,size,hash);
        ocs_previous.swap(current);
    }
}
// Scope duration is inclusive; these instruction charges isolate actual CPU polls.
struct ocs_instruction {
    uae_u64 start=0; unsigned kind=0; int cost_kind=-1; bool jump=false; unsigned jump_line=0;
    explicit ocs_instruction(unsigned pc) {
        if (!ocs_active) return;
        start=get_cycles();
        for(unsigned n=0;n<3;++n) if(pc>=ocs_cost_ranges[2*n] && pc<ocs_cost_ranges[2*n+1]) cost_kind=n;
        jump=get_word_debug(pc)==0x33c0 && get_long_debug(pc+2)==0xdff08a;
        jump_line=vpos;
        unsigned off=pc-ocs_h0;
        if (off==0x3293e || off==0x32942) kind=1;
        else if (off>=0x32a66 && off<0x32dba) {
            unsigned op=get_word_debug(pc);
            if(op==0x0113 || op==0x66fc) kind=2;
        }
    }
    ~ocs_instruction() {
        if (start && ocs_active) {
            ocs_cpu[kind]+=get_cycles()-start;
            if(cost_kind>=0) ocs_cost[cost_kind]+=get_cycles()-start;
            if(jump) fprintf(ocs_log,"J %llu %u %u %u\n",(unsigned long long)get_cycles(),
                jump_line,vpos,get_long_debug(ocs_h1+0x77fe));
        }
    }
};
