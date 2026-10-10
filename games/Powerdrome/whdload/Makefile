WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot

.DEFAULT_GOAL := all
VASMFLAGS ?=

.PHONY: all verify original FORCE
all: ../tmp/build/Powerdrome.slave

../tmp/build/Powerdrome.slave: Powerdrome.s FORCE
	mkdir -p ../tmp/build
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I$(NDK) -o $@ $<

verify:
	$(MAKE) all VASMFLAGS="-DVERIFY=1 $(VASMFLAGS)"
	cp ../tmp/build/Powerdrome.slave ../tmp/build/Powerdrome-verify.slave

original:
	mkdir -p ../tmp/build
	$(VASM) -m68000 -no-opt -Fhunkexe -nosym -I$(WHDLOAD)/Include -I$(NDK) -o ../tmp/build/Powerdrome-original.slave original/Powerdrome.s
	cmp ../tmp/build/Powerdrome-original.slave ../tmp/game/Powerdrome/Powerdrome.Slave
