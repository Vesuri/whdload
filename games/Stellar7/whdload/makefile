# The shared environment (as amiga/env.sh): WHDLoad 20.0 supplies the API headers and the
# public-domain KickEmu sources (kick13.s and its includes); include/lvo/ adapts their LVO include
# names to the host NDK.  The loader declares interface version 17 and uses no version-20-only
# features. Its game-specific startup is reconstructed from Psygore's supplied 1.0 slave; KickEmu
# is newer, so the result is not byte-identical to the original slave.
VASM ?= $(HOME)/.local/vasmm68k_mot
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
.PHONY: all clean verify FORCE
all: Stellar7.Slave
Stellar7.Slave: FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(WHDLOAD)/Src/sources" -I"$(NDK)" -o $@ Stellar7.s
clean:
	rm -f Stellar7.Slave

verify:
	$(MAKE) Stellar7.Slave VASMFLAGS="-DVERIFY=1 $(VERIFY_FLAGS)"
