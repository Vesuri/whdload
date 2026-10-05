# Host cross-build of JOTD's Test Drive II slave (the original uses BASM, see source/Makefile
# in the installer).  The output is not byte-identical to the shipped v1.5 slave: kick13.s is
# the official WHDLoad 20.0 sources/API headers are vendored, and BASM's date stamp is absent.
WHDLOAD ?= /path/to/WHDLoad
NDK ?= /path/to/sys-include
VASM ?= /path/to/vasmm68k_mot
VASMFLAGS ?=

.PHONY: all verify clean FORCE
all: TestDrive2.slave

# Always assemble: options must not leave a stale variant.
TestDrive2.slave: TestDrive2HD.s simulation.s simulation-verify.s simulation-patches.i render.s $(wildcard whdload/* include/*.i include/lvo/*.i) FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(NDK)" -o $@ $<

verify:
	$(MAKE) TestDrive2.slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f TestDrive2.slave
