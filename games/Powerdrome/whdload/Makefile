# The shared environment (as amiga/env.sh): WHDLoad 20.0 supplies the API headers and the KickEmu
# sources (kick13.s and its includes); include/lvo/ adapts their LVO include names to the NDK.
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot

.DEFAULT_GOAL := all
VASMFLAGS ?=

.PHONY: all verify coverage original original-verify FORCE
all: ../tmp/build/Powerdrome.slave

../tmp/build/mouse-sine.i: ../tools/mouse_sine.py
	mkdir -p ../tmp/build
	python3 $< $@

../tmp/build/Powerdrome.slave: Powerdrome.s ../tmp/build/mouse-sine.i FORCE
	mkdir -p ../tmp/build
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I$(WHDLOAD)/Include -I$(WHDLOAD)/Src/sources -I$(NDK) -o $@ $<

verify:
	$(MAKE) all VASMFLAGS="-DVERIFY=1 $(VASMFLAGS)"
	cp ../tmp/build/Powerdrome.slave ../tmp/build/Powerdrome-verify.slave

coverage:
	$(MAKE) all VASMFLAGS="-DVERIFY=1 -DCOVERAGE_INPUT=1 $(VASMFLAGS)"
	cp ../tmp/build/Powerdrome.slave ../tmp/build/Powerdrome-coverage.slave

original:
	mkdir -p ../tmp/build
	$(VASM) -m68000 -no-opt -Fhunkexe -nosym -I$(WHDLOAD)/Include -I$(NDK) -o ../tmp/build/Powerdrome-original.slave original/Powerdrome.s
	cmp ../tmp/build/Powerdrome-original.slave ../tmp/game/Powerdrome/Powerdrome.Slave

# Input-only original loader reference; the default original target stays byte-identical.
original-verify:
	mkdir -p ../tmp/build
	$(VASM) -m68000 -no-opt -pic -DVERIFY=1 -Fhunkexe -nosym -I. -I$(WHDLOAD)/Include -I$(NDK) -o ../tmp/build/Powerdrome-original-verify.slave original/Powerdrome.s
