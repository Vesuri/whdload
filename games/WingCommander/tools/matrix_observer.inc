// Phase 4 read-only host census. Scene cuts bound aprof without debugger stops.
// Config: hunk0, number of (PC, scene-id) pairs; ids 100 encode credits D5.
static void wc_matrix_observe(uae_u32 pc) {
    static bool initialized = false;
    static FILE* ledger = nullptr;
    static unsigned h0;
    static int scene = -1;
    static std::string directory;
    static std::vector<std::pair<unsigned,unsigned>> cuts;
    static std::vector<unsigned char> previous;
    if (!initialized) {
        initialized = true;
        const char* cfg = getenv("WC_MATRIX_CONFIG");
        const char* dir = getenv("WC_MATRIX_DIR");
        if (!cfg && !dir) return;
        if (!cfg || !dir) abort();
        FILE* input = fopen(cfg, "r");
        unsigned count;
        if (!input || fscanf(input, "%x %u", &h0, &count)!=2 || count>64) abort();
        for (unsigned i=0; i<count; ++i) {
            unsigned at, id;
            if (fscanf(input, "%x %u", &at, &id)!=2) abort();
            cuts.push_back({at,id});
        }
        fclose(input);
        directory=dir;
        ledger=fopen((directory+"/matrix-events.txt").c_str(), "wx");
        if (!ledger) abort();
    }
    if (!ledger) return;
    for (const auto& cut:cuts) {
        if (pc!=cut.first) continue;
        unsigned id=cut.second==100 ? 15+(regs.regs[5]&65535) : cut.second;
        if (id<=static_cast<unsigned>(scene) && scene>=0) continue;
        if (id>34 || id!=static_cast<unsigned>(scene+1)) abort();
        if (scene>=0) {
            char filename[64]; snprintf(filename,sizeof(filename),"/scene-%02d.aprof",scene);
            if (!aprof_stop((directory+filename).c_str())) abort();
        }
        scene=id; previous.clear();
        fprintf(ledger,"B %d %x %u %llu %08x\n",scene,pc,vsync_counter,
                (unsigned long long)get_cycles(),regs.cacr);
        fflush(ledger);
        if (id<34 && !aprof_start()) abort();
        break;
    }
    if (scene<0 || scene>=34) return;
    if (pc==h0+0x3378e) {
        fprintf(ledger,"P %d %u %llu %08x\n",scene,vsync_counter,
                (unsigned long long)get_cycles(),regs.cacr);
    }
    if (pc==h0+0x32028) {
        unsigned width=regs.regs[0]&65535, height=regs.regs[3]&65535;
        unsigned address=regs.regs[8], size=width*height;
        if (width!=320 || (height!=128 && height!=166 && height!=200) ||
            address+size>=0xa00000 || address<0x1000) abort();
        std::vector<unsigned char> current(size);
        unsigned bytes=0, blocks=0; bool changed=false, compared=previous.size()==size;
        for (unsigned i=0;i<size;++i) {
            current[i]=get_byte_debug(address+i);
            if (compared && current[i]!=previous[i]) { ++bytes; changed=true; }
            if ((i&31)==31) { blocks+=changed; changed=false; }
        }
        fprintf(ledger,"C %d %u %llu %u %u %u %u %08x\n",scene,vsync_counter,
                (unsigned long long)get_cycles(),size,compared,bytes,blocks,regs.cacr);
        previous.swap(current);
    }
}
