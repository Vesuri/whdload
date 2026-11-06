# Host cross-build of JOTD's Test Drive II slave (the original uses BASM, see source/Makefile
# in the installer).  The output is not byte-identical to the shipped v1.5 slave: kick13.s is
# the official WHDLoad 20.0 one and BASM's date stamp is absent.
# The shared environment (as amiga/env.sh): toolchain, NDK, and WHDLoad 20.0's API headers and
# KickEmu sources (copies next to this file win, as in the release's source/).  Override from
# the environment or make arguments.  Without
# ~/.local/vasmm68k_mot, vasmm68k_mot is taken from PATH.
AMIGA_TOOLCHAIN ?= $(HOME)/.local/opt
NDK ?= $(AMIGA_TOOLCHAIN)/m68k-amiga-elf/sys-include
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
VASM ?= $(firstword $(wildcard $(HOME)/.local/vasmm68k_mot) vasmm68k_mot)
VASMFLAGS ?=

.PHONY: all verify clean FORCE
all: TestDrive2.slave

# Always assemble: options must not leave a stale variant.
TestDrive2.slave: TestDrive2HD.s simulation.s simulation-verify.s simulation-patches.i render.s $(wildcard include/lvo/*.i) FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(WHDLOAD)/Src/sources" -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) TestDrive2.slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f TestDrive2.slave
