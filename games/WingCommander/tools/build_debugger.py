#!/usr/bin/env python3
"""Build the established debugger-native key route on a local shared-build copy.
Never modifies the shared installation. Requires its configured aprof build tree.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--intro-observer', action='store_true', help='read-only phase 3 PC/field observer')
    p.add_argument('--matrix-observer', action='store_true', help='phase 4 scene profiles and chunky change census')
    p.add_argument('--aprof-diagnostics', action='store_true', help='log unmatched context returns during diagnostic profiles')
    p.add_argument('--aprof-stable-pc', action='store_true', help='retain the executing PC/opcode before a control transfer changes it')
    p.add_argument('--aprof-stack-returns', action='store_true', help='diagnostic tracking of returns by their saved stack slot')
    p.add_argument('--matrix-nommu-counters', action='store_true', help='read-only scene/census hooks on the 040/060 NOMMU interpreter; no instruction-cost claims')
    p.add_argument('--frequency-clock', action='store_true', help='experimental numeric-clock scaling in colour-clock units; requires calibration')
    p.add_argument('--matrix-idle',action='store_true',help='read-only stopped-CPU transitions and STOP wait-loop accounting')
    p.add_argument('--matrix-dma',action='store_true',help='experimental per-field DMA summary; requires --matrix-observer')
    p.add_argument('--matrix-mmu030-counters',action='store_true',help='read-only scene counters on the cycle-exact 030 MMU interpreter')
    p.add_argument('--dma-cia-unsplit', action='store_true', help='diagnostic: preserve unrecorded CIA wait stepping; omit CIA wait-phase annotations')
    p.add_argument('--matrix-irq', action='store_true', help='diagnostic complete-call intervals for game VBL callbacks')
    a = p.parse_args()
    if a.matrix_irq and not a.matrix_observer:
        raise ValueError('--matrix-irq requires --matrix-observer')
    if a.dma_cia_unsplit and not a.matrix_dma:
        raise ValueError('--dma-cia-unsplit requires --matrix-dma')
    if a.matrix_mmu030_counters and not a.matrix_observer:
        raise ValueError('--matrix-mmu030-counters requires --matrix-observer')
    if a.matrix_idle and not a.matrix_observer:
        raise ValueError('--matrix-idle requires --matrix-observer')
    if a.matrix_dma and not a.matrix_observer:
        raise ValueError('--matrix-dma requires --matrix-observer')
    if a.matrix_nommu_counters and not a.matrix_observer:
        raise ValueError('--matrix-nommu-counters requires --matrix-observer')
    source = Path(os.environ.get('FSUAE_SOURCE', os.environ['AMIGA_SHARE']+'/fs-uae-aprof-build/fs-uae'))
    out = (ROOT/a.output).resolve()
    if (ROOT/'tmp').resolve() not in out.parents or out.exists():
        raise ValueError('choose a new output directory below tmp/')
    revision = subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if revision != 'b70b1180b44ab25b97cd66466c70879897d8a362':
        raise ValueError('unsupported shared source revision')
    for row in (ROOT/'manifest/debugger.tsv').read_text().splitlines():
        if not row or row.startswith('#'): continue
        name, digest = row.split('\t')
        if hashlib.sha256((source/name).read_bytes()).hexdigest() != digest:
            raise ValueError('shared build source differs: '+name)
    shutil.copytree(source, out, ignore=shutil.ignore_patterns('.git'))
    p = out/'src/keybuf.cpp'
    s = p.read_text()
    # Same native keyboard queue as the 4D Sports Driving debugger route.
    s += '''\n// Explicit debugger events must survive frontend focus-release suppression.
int record_key_debug(int kc) {
    ignore_next_release = false;
    return record_key_direct(kc);
}
'''
    p.write_text(s)
    p = out/'src/barto_gdbserver.cpp'
    s = p.read_text().replace('#include "sysconfig.h"', '#include "sysconfig.h"\nextern int record_key_debug(int);\nextern uae_u32 tc_030;', 1)
    anchor = '} else if(cmd == "aprof start") {'
    assert s.count(anchor) == 1
    s = s.replace(anchor, '''} else if(cmd == "inputcaps") {
        response += to_hex("key-raw-v1");
    } else if(cmd == "trace-window-all") {
        baseText = 0; sizeText = 0x7fffffff;
        response += to_hex("profile-window 00000000 7fffffff");
    } else if(cmd == "wc-audit") {
        char info[512];
        snprintf(info, sizeof(info), "WC_CPU model=%d mmu=%d exact=%d memory_exact=%d blitter_exact=%d multiplier=%d frequency=%d unit=%d cacr=%08x tc030=%08x immediate_blits=%d", currprefs.cpu_model, currprefs.mmu_model, currprefs.cpu_cycle_exact, currprefs.cpu_memory_cycle_exact, currprefs.blitter_cycle_exact, currprefs.cpu_clock_multiplier, currprefs.cpu_frequency, cpucycleunit, regs.cacr, tc_030, currprefs.immediate_blits);
        response += to_hex(info);
    } else if(cmd.substr(0, 4) == "key ") {
        unsigned key = 0; int pressed = -1; char extra;
        if(sscanf(cmd.c_str(), "key %x %d %c", &key, &pressed, &extra) == 2
           && key < 0x80 && (pressed == 0 || pressed == 1)) {
            unsigned raw = key | (pressed ? 0 : 0x80);
            response += record_key_debug(((raw << 1) | (raw >> 7)) & 0xff) ? "OK" : "E02";
        } else response += "E01";
    '''+anchor)
    p.write_text(s)
    if a.intro_observer or a.matrix_observer:
        target = out/'src/newcpu.cpp'
        code = target.read_text()
        anchor = 'struct cpu_profiler {'
        assert code.count(anchor) == 1
        code = code.replace(anchor, '#include "wc_intro_observer.inc"\n'+anchor)
        anchor = 'explicit cpu_profiler(uae_u32 pc) {'
        assert code.count(anchor) == 1
        code = code.replace(anchor, anchor+'\n        wc_observe(pc);')
        if a.matrix_observer:
            code=code.replace('struct cpu_profiler {','static void wc_matrix_observe(uae_u32 pc);\nstruct cpu_profiler {')
            code=code.replace('wc_observe(pc);','wc_observe(pc);\n        wc_matrix_observe(pc);')
            code=code.replace('// AITD-PROF-END','// AITD-PROF-END\n#include "wc_matrix_observer.inc"')
            shutil.copyfile(ROOT/'tools/matrix_observer.inc', out/'src/wc_matrix_observer.inc')
            if a.matrix_dma:
                code=code.replace('#include "wc_matrix_observer.inc"', '#include "wc_matrix_dma.inc"\n#include "wc_matrix_observer.inc"')
                shutil.copyfile(ROOT/'tools/matrix_dma.inc',out/'src/wc_matrix_dma.inc')
                observer=out/'src/wc_matrix_observer.inc'
                observer.write_text(observer.read_text().replace('scene=id; previous.clear();','scene=id; previous.clear();\n        wc_matrix_dma_cut(id);'))
                server=out/'src/barto_gdbserver.cpp'
                server_code=server.read_text().replace('#include "sysconfig.h"','#include "sysconfig.h"\nextern void wc_matrix_dma_vsync();',1)
                anchor='void vsync_pre() {'
                assert server_code.count(anchor)==1
                server_code=server_code.replace(anchor,anchor+'\n        wc_matrix_dma_vsync();')
                server.write_text(server_code)

        if a.matrix_idle:
            code=code.replace('#include "wc_matrix_observer.inc"', '#include "wc_matrix_idle.inc"\n#include "wc_matrix_observer.inc"')
            shutil.copyfile(ROOT/'tools/matrix_idle.inc',out/'src/wc_matrix_idle.inc')
            observer=out/'src/wc_matrix_observer.inc'
            observer_code=observer.read_text().replace('scene=id; previous.clear();','scene=id; previous.clear();\n        wc_matrix_idle_cut(id);')
            anchor='if (scene<0 || scene>=34) return;'
            assert observer_code.count(anchor)==1
            observer.write_text(observer_code.replace(anchor,anchor+'\n    wc_matrix_idle_pc(pc,h0);'))
            # Includes normal STOP/resume, reset and savestate restore assignments.
            assert code.count('regs.stopped = 1;')==2 and code.count('regs.stopped = 0;')==3
            for state in (0,1):
                assignment='regs.stopped = %d;' % state
                code=code.replace(assignment,assignment+'\n    wc_matrix_idle_event();')
            assert code.count('r->stopped = cputrace.stopped;')==3
            code=code.replace('r->stopped = cputrace.stopped;','r->stopped = cputrace.stopped;\n    wc_matrix_idle_event();')
            start=code.index('void do_cycles_stop(int c)')
            end=code.index('void m68k_setstopped (void)',start)
            body=code[start:end]
            body=body.replace('{\n','{\n    const uae_u64 wc_idle_start = get_cycles();\n    const bool wc_idle_was_stopped = regs.stopped != 0;\n',1)
            at=body.rfind('}')
            body=body[:at]+'    wc_matrix_idle_wait(wc_idle_start,wc_idle_was_stopped);\n'+body[at:]
            code=code[:start]+body+code[end:]

        if a.matrix_irq:
            code=code.replace('#include "wc_matrix_observer.inc"', '#include "wc_matrix_irq.inc"\n#include "wc_matrix_observer.inc"')
            shutil.copyfile(ROOT/'tools/matrix_irq.inc',out/'src/wc_matrix_irq.inc')
            observer=out/'src/wc_matrix_observer.inc'
            observer_code=observer.read_text().replace('scene=id; previous.clear();','scene=id; previous.clear();\n        wc_matrix_irq_cut(id);')
            anchor='if (scene<0 || scene>=34) return;'
            assert observer_code.count(anchor)==1
            observer.write_text(observer_code.replace(anchor,anchor+'\n    wc_matrix_irq_pc(pc,h0);'))

        if a.matrix_nommu_counters:
            # 040/060 use this interpreter without the Barto instruction profiler.
            # Observe the next PC before fetch, without changing emulated cycles.
            start = code.index('static void m68k_run_3ce (void)')
            end = code.index('static void m68k_run_3p(void)', start)
            body = code[start:end]
            anchor = 'r->instruction_pc = m68k_getpc();'
            assert body.count(anchor) == 1
            body = body.replace(anchor, anchor+'\n                wc_observe(r->instruction_pc);\n                wc_matrix_observe(r->instruction_pc);')
            code = code[:start]+body+code[end:]
        if a.matrix_mmu030_counters:
            start=code.index('static void m68k_run_mmu030 (void)')
            end=code.index('static void m68k_run_3ce (void)',start)
            body=code[start:end]
            anchor='insretry:\n'
            assert body.count(anchor)==1
            # Internal MMU retries jump past the observer, so a retried
            # instruction does not add another scene/publication/census event.
            body=body.replace(anchor,'                wc_observe(m68k_getpc());\n                wc_matrix_observe(m68k_getpc());\n'+anchor)
            code=code[:start]+body+code[end:]
        target.write_text(code)
        shutil.copyfile(ROOT/'tools/intro_observer.inc', out/'src/wc_intro_observer.inc')
    if a.aprof_stable_pc or a.matrix_observer or a.aprof_stack_returns:
        target = out/'src/newcpu.cpp'
        code = target.read_text()
        start = '\t\t\t\tif (aprof_on) aprof_before();'
        end = '\t\t\t\tif (aprof_on) aprof_after(r->instruction_pc, r->opcode);'
        assert code.count(start) == code.count(end) == 1
        # A local block keeps the core's existing goto-cont path outside these
        # initializations. Guest execution and the Barto hook stay unchanged.
        code = code.replace(start, '\t\t\t\t{ const uae_u32 wc_pc = r->instruction_pc;\n'
                                  '\t\t\t\t  const uae_u16 wc_opcode = r->opcode;\n'+start)
        code = code.replace(end, '\t\t\t\tif (aprof_on) aprof_after(wc_pc, wc_opcode);\n\t\t\t\t}')
        code = code.replace('fprintf(f, "AITDPROF 1\\n");',
                            'fprintf(f, "AITDPROF 1\\nsource_pc_stable 1\\n");')
        target.write_text(code)
    if a.aprof_diagnostics:
        target = out/'src/newcpu.cpp'
        code = target.read_text()
        anchor = '\tif (rte) aprof_unmatched_rte++; else aprof_unmatched_rts++;'
        assert code.count(anchor) == 1
        code = code.replace('static void aprof_pop(uae_u32 newpc, bool rte)', 'static void aprof_pop(uae_u32 newpc, bool rte, uae_u32 pc)')
        code = code.replace('aprof_pop(m68k_getpc(), false);', 'aprof_pop(m68k_getpc(), false, pc);')
        code = code.replace('aprof_pop(m68k_getpc(), true);', 'aprof_pop(m68k_getpc(), true, pc);')
        code = code.replace(anchor, r'''	write_log("WC_UNMATCH rte=%d pc=%08x next=%08x sp=%08x depth=%d\n",
            rte, pc, newpc, m68k_areg(regs,7), aprof_depth);
        for (int i=aprof_depth-1; i>=0 && i>=aprof_depth-4; --i) {
            const auto& fr=aprof_stack[i];
            write_log("WC_FRAME ret=%08x kind=%u target=%08x\n", fr.ret, fr.kind, aprof_nodes[fr.node].target);
        }
''' + anchor)
        target.write_text(code)
    if a.aprof_stack_returns:
        target = out/'src/newcpu.cpp'
        code = target.read_text()
        old = 'struct aprof_frame { uae_u32 ret; uae_u32 node; uae_u8 kind; };'
        assert code.count(old) == 1
        code = code.replace(old, 'static uae_u32 aprof_entry_sp;\nstatic uae_u64 aprof_adjusted_returns;\n'
                                'struct aprof_frame { uae_u32 ret; uae_u32 node; uae_u8 kind; uae_u32 slot; };')
        code = code.replace('aprof_stack[aprof_depth++] = {ret, node, kind};',
                            'aprof_stack[aprof_depth++] = {ret, node, kind, m68k_areg(regs,7)};')
        if a.aprof_diagnostics:
            code = code.replace('bool rte, uae_u32 pc)', 'bool rte, uae_u32 pc, uae_u32 slot)')
            code = code.replace('aprof_pop(m68k_getpc(), false, pc);',
                                'aprof_pop(m68k_getpc(), false, pc, aprof_entry_sp + (opcode == 0x4e77 ? 2 : 0));')
            code = code.replace('aprof_pop(m68k_getpc(), true, pc);',
                                'aprof_pop(m68k_getpc(), true, pc, aprof_entry_sp);')
        else:
            code = code.replace('bool rte)', 'bool rte, uae_u32 slot)', 1)
            code = code.replace('aprof_pop(m68k_getpc(), false);',
                                'aprof_pop(m68k_getpc(), false, aprof_entry_sp + (opcode == 0x4e77 ? 2 : 0));')
            code = code.replace('aprof_pop(m68k_getpc(), true);',
                                'aprof_pop(m68k_getpc(), true, aprof_entry_sp);')
        old = '\t\tif (fr.ret == newpc || ((fr.kind == 10 || fr.kind == 11) && fr.ret + 2 == newpc)) {'
        assert code.count(old) == 1
        code = code.replace(old, r'''        const bool saved_slot = !rte && fr.kind == 0 && fr.slot == slot;
        if (saved_slot || fr.ret == newpc || ((fr.kind == 10 || fr.kind == 11) && fr.ret + 2 == newpc)) {
            if (saved_slot && fr.ret != newpc) {
                ++aprof_adjusted_returns;
                write_log("WC_ADJUSTED slot=%08x saved=%08x next=%08x target=%08x\n", slot, fr.ret, newpc, aprof_nodes[fr.node].target);
            }
''')
        code = code.replace('if (aprof_on) aprof_before();',
                            'aprof_entry_sp = m68k_areg(regs,7);\n                if (aprof_on) aprof_before();')
        code = code.replace('aprof_depth = 0;\n\taprof_hi_cyc', 'aprof_depth = 0;\n    aprof_adjusted_returns = 0;\n\taprof_hi_cyc')
        code = code.replace('fprintf(f, "AITDPROF 1\\nsource_pc_stable 1\\n");',
                            'fprintf(f, "AITDPROF 1\\nsource_pc_stable 1\\nstack_return_slots 1\\nadjusted_returns %llu\\n", (unsigned long long)aprof_adjusted_returns);')
        target.write_text(code)
    if a.frequency_clock:
        target = out/'src/newcpu.cpp'
        code = target.read_text()
        old = 'cpucycleunit = CYCLE_UNIT * baseclock / currprefs.cpu_frequency;'
        assert code.count(old) == 1
        # get_cycles uses CYCLE_UNIT units per colour clock. The known stock
        # 020 multiplier yields 128 units at four colour clocks per CPU clock.
        # baseclock is eight colour clocks; widen before multiplying.
        new = 'cpucycleunit = (uae_u64)CYCLE_UNIT * (baseclock / 8) / currprefs.cpu_frequency;'
        code = code.replace(old, new)
        target.write_text(code)
    if a.dma_cia_unsplit:
        target = out/'src/cia.cpp'
        code = target.read_text()
        start = code.index('static int cia_cycles(')
        end = code.index('static void cia_wait_post(', start)
        part = code[start:end]
        # Record actual CIA accesses as before, but leave the CPU's delay
        # calls identical to DMA-off. Wait-phase annotations are diagnostic
        # metadata and are not bus ownership records.
        old = 'if (currprefs.cpu_memory_cycle_exact && debug_dma) {'
        assert part.count(old) == 1
        part = part.replace(old, 'if (false) { // WC: preserve CIA wait stepping')
        old = 'if (debug_dma) {'
        assert part.count(old) == 1
        part = part.replace(old, 'if (false) { // WC: keep sync and access delay combined')
        target.write_text(code[:start] + part + code[end:])
    # Existing configured dependencies and objects are shared-build inputs; make
    # recompiles the changed translation units and links a new local binary.
    env = dict(os.environ, TMPDIR=str(out))
    subprocess.run(['/usr/bin/make','-j4','fs-uae'],cwd=out,env=env,check=True)
    subprocess.run([str(out/'fs-uae'),'--version'],check=True)
    print('local debugger:',out.relative_to(ROOT)/'fs-uae')

if __name__ == '__main__': main()
