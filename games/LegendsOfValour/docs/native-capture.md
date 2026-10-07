# Native Barto captures

The restored arm64 FS-UAE is at `~/.local/share/amiga/fs-uae-arm/fs-uae`, revision
`b70b1180b44ab25b97cd66466c70879897d8a362`. Host LLDB attachment timed out;
the opt-in `PROFILE_WINDOW=guest` mode configures its profiler through the guest
DOS metadata instead. The shared executable is unchanged.

The VERIFY-only `PROFILER_WINDOW` fixture runs at the tape anchor in VBL context.
It saves SR, the current process's segment-list/task-number fields and 32 chip
scratch bytes, masks interrupts, and presents a synthetic segment while paused.
The harness queries qOffsets and requires the expected acknowledgement, then
runs the restoration routine before tracing. `profile_window_check.py` compares
the saved process fields and all scratch bytes with snapshots after restoration.
Normal and ordinary VERIFY builds exclude this fixture.

Barto stores RAM PCs relative to the profiler start, while physical ROM PCs
and IRQ markers remain absolute. See the exact revision's
[newcpu.cpp](https://github.com/grahambates/fs-uae/blob/b70b1180b44ab25b97cd66466c70879897d8a362/src/newcpu.cpp)
and [gdb server](https://github.com/grahambates/fs-uae/blob/b70b1180b44ab25b97cd66466c70879897d8a362/src/barto_gdbserver.cpp).
`lov.py` retains the acknowledged base in `trace.pc-base`; `barto.py` normalizes
RAM PCs without changing registers, costs, ROM PCs or IRQ markers. No sidecar
means legacy base zero, regardless of the trace section metadata.

The retained `tmp/prof/w3-guest-spin-a500-off` 100-field gameplay window passes
restoration checking and records 100 VBL entries, five display intervals across
82 fields, and six completed C2P calls. A parser offset error initially hid those
entries; normalization recovers them. Synthetic records also verify RAM, physical
ROM, IRQ, STOP and unchanged registers. This validates the capture mechanism,
not any rendering optimization.

The attempted RSP relay produced PCs during boot but none during its gameplay
window; those captures are excluded and the relay was removed. Intel tools also
stalled before execution. A native vasm 2.0f built under ignored tmp produces
normal/ordinary VERIFY bytes identical to the earlier vasm 1.9 outputs.

Use the normal §7 machine settings and serial capture rules, adding:

```sh
FSUAE="$HOME/.local/share/amiga/fs-uae-arm/fs-uae" PROFILE_WINDOW=guest \
  VASM=../tmp/vasm-native-src/vasm/vasmm68k_mot tools/fixed_window.sh OUT
```

Keep the sidecar with its trace and retained slave/listing. All binaries and
capture evidence stay in ignored tmp; never operate `amiga/.run` for captures.

Breakpoint waits now continue in the background, keeping GDB's command channel
available. `UNTIL_TIMEOUT` defaults to 1,800 seconds; an expired wait stops the
owned capture and deletes its temporary breakpoints before reporting the error.
This lets the caller dump the stopped state and quit normally. It avoids the old
synchronous wait's additional ten-minute dump timeout when an input route stalls.
The bounded check in `tmp/prof/timeout-recovery` verified an unreachable breakpoint,
a responsive stopped-state query, a subsequent successful breakpoint, and normal
cleanup in `.cap`. This is debugger recovery evidence, not a performance measurement.
