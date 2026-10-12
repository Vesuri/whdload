// Read-only complete-call intervals for the three registered game VBL callbacks.
// Elapsed scope time includes callees and any preemption, not CPU self time.
static FILE* wc_irq_output = nullptr;
struct wc_irq_scope { unsigned id, kind, sp, ret; };
static std::vector<wc_irq_scope> wc_irq_active;
static unsigned wc_irq_serial = 0;
static void wc_matrix_irq_cut(unsigned scene) {
    if (scene == 0) {
        const char* enabled = getenv("WC_MATRIX_IRQ");
        if (!enabled || strcmp(enabled,"1")) return;
        const char* directory = getenv("WC_MATRIX_DIR");
        if (!directory) abort();
        std::string path = std::string(directory)+"/irq-events.txt";
        wc_irq_output = fopen(path.c_str(),"wx");
        if (!wc_irq_output) abort();
    }
    if (!wc_irq_output) return;
    fprintf(wc_irq_output,"B %u %llu\n",scene,(unsigned long long)get_cycles());
    fflush(wc_irq_output);
    if (scene == 34) {
        // A partial callback at the final endpoint must not become a full call.
        if (!wc_irq_active.empty()) abort();
        fclose(wc_irq_output); wc_irq_output = nullptr;
    }
}
static void wc_matrix_irq_pc(unsigned pc, unsigned h0) {
    if (!wc_irq_output) return;
    const unsigned sp = m68k_areg(regs,7);
    if (!wc_irq_active.empty()) {
        const wc_irq_scope& scope = wc_irq_active.back();
        if (pc == scope.ret && sp == scope.sp+4) {
            fprintf(wc_irq_output,"R %u %llu %x %x\n",scope.id,
                    (unsigned long long)get_cycles(),pc,sp);
            wc_irq_active.pop_back();
        }
    }
    const unsigned offsets[] = {0x34162,0x27810,0x33e62};
    for (unsigned kind=0; kind<3; ++kind) {
        if (pc != h0+offsets[kind]) continue;
        if (sp < 0x100 || sp > 0x9ffffc || (sp&1) || wc_irq_active.size()>=16) abort();
        const unsigned ret = get_long_debug(sp);
        wc_irq_scope scope = {++wc_irq_serial,kind,sp,ret};
        wc_irq_active.push_back(scope);
        fprintf(wc_irq_output,"E %u %u %llu %x %x %x\n",scope.id,kind,
                (unsigned long long)get_cycles(),pc,sp,ret);
    }
}
