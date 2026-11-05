// Authored observer: no guest writes, cache flushes, debugger pauses or DMA tracing.
static uae_u32 wc_visual_read(uaecptr addr) {
    if(currprefs.cpu_data_cache && (regs.cacr & 0x80000000)) {
        struct cache040 *c=&dcaches040[(addr>>4)&cachedsets04060mask];
        uae_u32 tag=(addr & ~15)&cachedtag04060mask;
        for(int line=0;line<CACHELINES040;line++)
            if(c->valid[line] && c->tag[line]==tag) return dcache040_get_data(addr,c,line,0);
    }
    return get_byte_debug(addr);
}
// Read-only visual audit; no debugger/profiler, cache flush, or guest writes.
static void wc_visual_observe(uae_u32 pc) {
    static const char *path = getenv("WC_VISUAL_OUT");
    if (!path || !getenv("WC_VISUAL_H0") || !getenv("WC_VISUAL_H3")) return;
    static uae_u32 h0 = strtoul(getenv("WC_VISUAL_H0"), nullptr, 16);
    static uae_u32 h3 = strtoul(getenv("WC_VISUAL_H3"), nullptr, 16);
    static unsigned frames=0, bad=0, shots=0;
    if (shots) return;
    static unsigned limit=getenv("WC_VISUAL_FRAMES") ? atoi(getenv("WC_VISUAL_FRAMES")) : 0;
    if(frames==0 && pc==h0+0x31ff2){char n[2048];snprintf(n,sizeof n,"%s/cpu.txt",path);FILE*f=fopen(n,"w");if(f){fprintf(f,"tc=%08x dtt0=%08x dtt1=%08x urp=%08x srp=%08x cache_state=%02x\n",regs.tcr,regs.dtt0,regs.dtt1,regs.urp,regs.srp,mmu_cache_state);fclose(f);}}
    if (((!limit && pc == h3 + 0xde0) || (limit && frames >= limit)) && shots == 0) {
        shots = 1;
        fsemu_screenshot_capture();
        char name[2048]; snprintf(name,sizeof name,"%s/done.txt",path);
        FILE *f=fopen(name,"w"); if(f){fprintf(f,"frames=%u bad=%u cacr=%08x\n",frames,bad,regs.cacr);fclose(f);}
    }
    if (pc != h0 + 0x31ff2) return;
    unsigned height=m68k_dreg(regs,3)&65535;
    if(height!=128 && height!=166 && height!=200) return;
    uae_u32 src=m68k_areg(regs,0),dst=m68k_areg(regs,1);
    unsigned n=320*height, stride=n/8;
    std::vector<unsigned char> source(n), rawsource(n), plane(n), rawplane(n);
    for(unsigned i=0;i<n;i++) {
        source[i]=wc_visual_read(src+i);
        rawsource[i]=get_byte_debug(src+i);
        plane[i]=wc_visual_read(dst+i);
        rawplane[i]=get_byte_debug(dst+i);
    }
    unsigned cpu_diff=0,dma_diff=0,dirty=0;
    for(unsigned i=0;i<n;i++) {
        unsigned value=0,raw=0;
        for(unsigned b=0;b<8;b++) {
            unsigned off=b*stride+i/8, bit=7-(i&7);
            value|=((plane[off]>>bit)&1)<<b;
            raw|=((rawplane[off]>>bit)&1)<<b;
        }
        cpu_diff+=value!=source[i];dma_diff+=raw!=source[i];dirty+=plane[i]!=rawplane[i];
    }
    char name[2048];snprintf(name,sizeof name,"%s/frames.txt",path);
    FILE *f=fopen(name,"a");if(f){fprintf(f,"%u %08x %08x %u %u %u %u %08x\n",frames,src,dst,height,cpu_diff,dma_diff,dirty,regs.cacr);fclose(f);}
    bool differs=cpu_diff||dma_diff;
    if(differs) bad++;
    if(frames==0 || (differs && bad<=8)) {
        const char *names[]={"source","rawsource","plane","rawplane"};
        const unsigned char *data[]={source.data(),rawsource.data(),plane.data(),rawplane.data()};
        for(unsigned i=0;i<4;i++) { snprintf(name,sizeof name,"%s/%u-%s.bin",path,frames,names[i]);FILE*f=fopen(name,"wb");if(f){fwrite(data[i],1,n,f);fclose(f);} }
    }
    frames++;
}
