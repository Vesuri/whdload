# Open work

Set up 18.11.2026: `src/` is JOTD's v3.1 source with three changes that make vasm assemble
it, equivalent to the shipped slaves apart from the newer KickEmu (`development.md`,
"Build"). All three variants boot to the duty roster. No improvement work yet.

## Next

1. **Choose the work.** Profile each version in flight on its machines (AmigaXDev's
   playbook) before choosing; the flight engine (`gs2.run`) is the likely target.
2. **A first release** needs a dated `$VER` and info string in each slave
   (`$VER: slave <version> (dd.mm.yyyy)`, `docs/releasing.md`), and the ReadMe entry
   above JOTD's.

## Also seen

- The AGA slave's `_cb_dosLoadSeg` clears long 0 on every `LoadSeg`, and `set_copperlist`
  writes a copper end there for the game's `COPJMP2` to 0 (`internals.md`).
- The CD32 slave keeps `DEBUG` set, and its patch list is dead code (`_patch_gs2000`
  returns first).
- The ReadMe's memory figures and quit key (F10) do not match the slaves ($5d).
