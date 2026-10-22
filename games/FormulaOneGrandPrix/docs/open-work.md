# Current scope

Goals: improve the game's performance, especially on 68020-with-fast-RAM and faster
Amigas, and make the simulation speed independent of the frame rate.

The launcher boots the installed game, `tools/f1gp.py quickrace` drives it from boot to
the first field of a Quick Race at Silverstone, and `tools/race_profile.py` profiles
three 10-second phases of that race. `docs/internals.md` records the
verified slave and executable structure. B1 has a byte-identical local reconstruction of the original slave and decoded patch lists.
No new slave has passed a gameplay gate yet.

# Next

The plan is [docs/plan.md](plan.md): real-time game speed on every machine, smooth
pictures up to 50 fps on 68020+ by extrapolation, and the performance work, in steps
`A1`–`G4`. Its first steps are `A1`–`A3`, `A5`, `A6` (time sources, the main loops,
simulation versus presentation, publication, interrupts) and `B1`–`B4` (rebuilding the
slave, which has no source). This session is authorised for B1–B4 and A1, A2, A5, A6 (A3 if time permits).
Next: B2, the new loader using shared kick13. The A audits remain open.
