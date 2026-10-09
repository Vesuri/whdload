WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot

.PHONY: original
original:
	mkdir -p ../tmp/build
	$(VASM) -m68000 -no-opt -Fhunkexe -nosym -I$(WHDLOAD)/Include -I$(NDK) -o ../tmp/build/Powerdrome-original.slave original/Powerdrome.s
	cmp ../tmp/build/Powerdrome-original.slave ../tmp/game/Powerdrome/Powerdrome.Slave
