# Host cross-build of JOTD's Test Drive II slave (the original uses BASM, see source/Makefile
# in the installer).  The output is not byte-identical to the shipped v1.5 slave: kick13.s is
# the vendored copy (whdload/), and BASM's date stamp is absent.
WHDLOAD ?= /path/to/WHDLoad
NDK ?= /path/to/sys-include
VASM ?= /path/to/vasmm68k_mot
VASMFLAGS ?=

.PHONY: all clean FORCE
all: TestDrive2.slave

# Always assemble: options must not leave a stale variant.
TestDrive2.slave: TestDrive2HD.s FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(WHDLOAD)/Include" -I"$(NDK)" -o $@ $<

clean:
	rm -f TestDrive2.slave
