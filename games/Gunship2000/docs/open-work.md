# Open work

Set up 18.11.2026: `src/` is JOTD's v3.1 source with three changes that make vasm assemble
it, equivalent to the shipped slaves apart from the newer KickEmu (`development.md`,
"Build"). All three variants boot to the duty roster. No improvement work yet.

## Next

1. **Choose the work.** Profile each version in flight on its machines (AmigaXDev's
   playbook) before choosing; the flight engine (`gs2.run`) is the likely target.
2. **Release 4.0b** (18.11.2026) is set: `slave_version` gives each slave's info text and
   `$VER: Gunship2000<Variant>.slave 4.0b (18.11.2026)`, the info text credits Vesuri, and
   the ReadMe entry above JOTD's says what changed (the WHDLoad 20.1 KickEmu). `make dist`
   packs it; not yet published. Bump the version and the entry as improvements land.

## Also seen

- The AGA slave's `_cb_dosLoadSeg` clears long 0 on every `LoadSeg`, and `set_copperlist`
  writes a copper end there for the game's `COPJMP2` to 0 (`internals.md`).
- The CD32 slave keeps `DEBUG` set, and its patch list is dead code (`_patch_gs2000`
  returns first).
- The ReadMe's memory figures and quit key (F10) do not match the slaves ($5d).
