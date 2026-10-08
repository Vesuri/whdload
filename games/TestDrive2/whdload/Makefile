# Host cross-build of JOTD's Test Drive II slave (the original uses BASM, see source/Makefile
# in the installer).  The output is not byte-identical to the shipped v1.5 slave: kick13.s is
# the official WHDLoad 20.0 sources/API headers are vendored, and BASM's date stamp is absent.
# The shared ~/.local toolchain (as amiga/env.sh); override from the environment or make
# arguments. Without ~/.local/vasmm68k_mot, vasmm68k_mot is taken from PATH.
AMIGA_TOOLCHAIN ?= $(HOME)/.local/opt
NDK ?= $(AMIGA_TOOLCHAIN)/m68k-amiga-elf/sys-include
VASM ?= $(firstword $(wildcard $(HOME)/.local/vasmm68k_mot) vasmm68k_mot)
VASMFLAGS ?=

.PHONY: all verify clean FORCE
all: TestDrive2.slave

# Always assemble: options must not leave a stale variant.
TestDrive2.slave: TestDrive2HD.s simulation.s simulation-verify.s simulation-patches.i render.s $(wildcard whdload/* include/*.i include/lvo/*.i) FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) TestDrive2.slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f TestDrive2.slave
