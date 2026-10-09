VASM ?= $(HOME)/.local/vasmm68k_mot
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
.PHONY: all clean FORCE
all: Stellar7.Slave
Stellar7.Slave: FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym -I. -Iinclude -I"$(NDK)" -o $@ Stellar7.s
clean:
	rm -f Stellar7.Slave
