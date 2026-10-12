// Read-only host observer for the validated cycle-exact 68020 interpreter.
// No guest writes, cycle changes, input injection or debugger stops.
// Config: hunk0 hunk1 hunk3 (hex), followed by absolute PCs (hex).
#include <algorithm>
static void wc_observe(uae_u32 pc) {
    static bool initialized = false;
    static FILE* output = nullptr;
    static unsigned h0, h1, h3;
    static std::vector<unsigned> pcs;
    if (!initialized) {
        initialized = true;
        const char* config = getenv("WC_OBSERVER_CONFIG");
        const char* dest = getenv("WC_OBSERVER_OUTPUT");
        if (!config && !dest) return;
        FILE* input = config ? fopen(config, "r") : nullptr;
        if (!input || !dest || fscanf(input, "%x %x %x", &h0, &h1, &h3) != 3) abort();
        unsigned value;
        while (fscanf(input, "%x", &value) == 1) pcs.push_back(value);
        fclose(input);
        if (pcs.empty() || h0 < 0x200000 || h1 < 0x200000 || h3 < 0x200000) abort();
        std::sort(pcs.begin(), pcs.end());
        output = fopen(dest, "wx");
        if (!output) abort();
        fprintf(output, "# pc field hsync cycles vpos maxvpos baseclock cycleunit d0..a7 clock music_position order row tick active copper_index\n");
    }
    if (!output || !std::binary_search(pcs.begin(), pcs.end(), pc)) return;
    fprintf(output, "%x %u %u %llu %d %d %d %d", pc, vsync_counter, hsync_counter,
            (unsigned long long)get_cycles(), vpos, maxvpos, baseclock, cpucycleunit);
    for (unsigned n=0; n<16; ++n) fprintf(output, " %x", regs.regs[n]);
    // Fixed, calibrated game data addresses only; never custom/device reads.
    fprintf(output, " %u %u %u %u %u %u %u\n",
            get_long_debug(h1+0x7f02), get_word_debug(h1+0x4bbc),
            get_byte_debug(h1+0x51a1-2), get_word_debug(h1+0x51ae-2),
            get_byte_debug(h1+0x51a0-2), get_byte_debug(h1+0x51a7-2),
            get_word_debug(h0+0x33210));
    fflush(output);
}
