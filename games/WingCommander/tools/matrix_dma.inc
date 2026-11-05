// Read-only DMA summaries from the debugger's completed field buffer.
// Enabling debug_dma itself is experimental until neutrality checks pass.
static FILE* wc_dma_output = nullptr;
static std::vector<std::pair<uae_u64,unsigned>> wc_dma_cuts;
static void wc_matrix_dma_cut(unsigned scene) {
    if (scene == 0) {
        const char* enabled = getenv("WC_MATRIX_DMA");
        if (!enabled || strcmp(enabled,"1")) return;
        const char* directory = getenv("WC_MATRIX_DIR");
        if (!directory) abort();
        std::string filename = std::string(directory)+"/dma-events.txt";
        wc_dma_output=fopen(filename.c_str(),"wx");
        if (!wc_dma_output) abort();
        record_dma_reset(1);
    }
    if (wc_dma_output) wc_dma_cuts.push_back({get_cycles(),scene});
}
void wc_matrix_dma_vsync() {
    if (!wc_dma_output || wc_dma_cuts.empty()) return;
    dma_rec* records=get_dma_records();
    if (!records) abort();
    unsigned heights=0, lengths[1000], slots=0;
    for (unsigned y=0; y<1000; ++y) {
        if (records[y*256].end) { heights=y; break; }
        unsigned width=0;
        for (unsigned x=1; x<256; ++x) {
            if (records[y*256+x].end) { width=x; break; }
        }
        if (!width) return; // first incomplete field has no complete geometry
        lengths[y]=width; slots+=width;
    }
    if (!heights || !slots) return;
    const uae_u64 end=get_cycles();
    const uae_u64 span=(uae_u64)slots*CYCLE_UNIT;
    if (end<span) return;
    const uae_u64 start=end-span;
    unsigned counts[35][DMARECORD_MAX+1]={};
    unsigned totals[DMARECORD_MAX+1]={};
    unsigned ordinal=0, cut=0;
    for (unsigned y=0; y<heights; ++y) {
        for (unsigned x=0; x<lengths[y]; ++x,++ordinal) {
            const uae_u64 at=start+(uae_u64)ordinal*CYCLE_UNIT;
            while (cut+1<wc_dma_cuts.size() && wc_dma_cuts[cut+1].first<=at) ++cut;
            int type=records[y*256+x].type;
            if (type<0 || type>=DMARECORD_MAX) type=DMARECORD_MAX;
            ++totals[type];
            if (at>=wc_dma_cuts[cut].first && wc_dma_cuts[cut].second<34)
                ++counts[wc_dma_cuts[cut].second][type];
        }
    }
    fprintf(wc_dma_output,"F %u %llu %llu %u %u",vsync_counter,
            (unsigned long long)start,(unsigned long long)end,heights,slots);
    for (unsigned n=0;n<=DMARECORD_MAX;++n) fprintf(wc_dma_output," %u",totals[n]);
    fputc('\n',wc_dma_output);
    for (unsigned scene=0;scene<34;++scene) {
        unsigned total=0; for (unsigned n=0;n<=DMARECORD_MAX;++n) total+=counts[scene][n];
        if (!total) continue;
        fprintf(wc_dma_output,"D %u %u",scene,vsync_counter);
        for (unsigned n=0;n<=DMARECORD_MAX;++n) fprintf(wc_dma_output," %u",counts[scene][n]);
        fputc('\n',wc_dma_output);
    }
    fflush(wc_dma_output);
    // The independent Barto sample may have disabled recording at a field end.
    if (wc_dma_cuts.back().second<34) debug_dma=1;
}
