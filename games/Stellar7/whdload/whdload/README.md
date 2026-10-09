# WHDLoad 20.0 sources

Public-domain KickEmu sources and API headers copied verbatim from the shared
WHDLoad 20.0 developer package. The lvo include aliases adapt the include
names to the host NDK. There are no local changes to the vendored sources.

The Stellar 7 loader declares interface version 17 and uses no version-20-only
features. Its original game-specific startup behavior is reconstructed from
Psygore's supplied 1.0 slave; KickEmu is updated, so this is not byte-identical
to the original slave and behavioral equivalence still needs verification.
