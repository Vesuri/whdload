// Read-only STOP-state transitions plus an independent STOP wait-loop counter.
// Busy waits remain executing CPU time, not stopped-CPU time.
static FILE* wc_idle_output = nullptr;
static bool wc_idle_stopped = false;
static uae_u64 wc_idle_stop_pcs[2] = {};
static void wc_matrix_idle_pc(uae_u32 pc, uae_u32 h0) {
    if (!wc_idle_output) return;
    if (pc == h0+0x34074) ++wc_idle_stop_pcs[0];
    if (pc == h0+0x3408e) ++wc_idle_stop_pcs[1];
}
static uae_u64 wc_idle_wait_units = 0, wc_idle_wait_calls = 0;
static void wc_matrix_idle_event() {
    if (!wc_idle_output) return;
    const bool stopped = regs.stopped != 0;
    if (stopped == wc_idle_stopped) return;
    fprintf(wc_idle_output, "T %llu %u\n", (unsigned long long)get_cycles(), stopped);
    wc_idle_stopped = stopped;
}
static void wc_matrix_idle_cut(unsigned scene) {
    if (scene == 0) {
        const char* enabled = getenv("WC_MATRIX_IDLE");
        if (!enabled || strcmp(enabled,"1")) return;
        const char* directory = getenv("WC_MATRIX_DIR");
        if (!directory) abort();
        std::string filename = std::string(directory)+"/idle-events.txt";
        wc_idle_output = fopen(filename.c_str(),"wx");
        if (!wc_idle_output) abort();
        wc_idle_stopped = regs.stopped != 0;
    }
    if (!wc_idle_output) return;
    // Every stopped-state assignment is hooked; a missed transition is an error.
    if (wc_idle_stopped != (regs.stopped != 0)) abort();
    fprintf(wc_idle_output,"B %u %llu %u %llu %llu %llu %llu\n",scene,
            (unsigned long long)get_cycles(),wc_idle_stopped,
            (unsigned long long)wc_idle_wait_units,(unsigned long long)wc_idle_wait_calls,
            (unsigned long long)wc_idle_stop_pcs[0],(unsigned long long)wc_idle_stop_pcs[1]);
    fflush(wc_idle_output);
    if (scene == 34) { fclose(wc_idle_output); wc_idle_output = nullptr; }
}
static void wc_matrix_idle_wait(uae_u64 start, bool stopped) {
    if (!wc_idle_output) return;
    if (stopped != (regs.stopped != 0)) abort();
    if (!stopped) return; // initial STOP instruction latency is not stopped time
    wc_idle_wait_units += get_cycles()-start;
    ++wc_idle_wait_calls;
}
