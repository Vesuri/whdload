# Host cross-build of the Battlehawks 1942 slave.
#   make            WHDLoad 20.0 KickEmu slave (Battlehawks1942.s, vendored whdload/ + include/)
#   make verify     the same with VERIFY instruments (tape.s)
#   make original   Galahad's v1.0, reconstructed (original/Battlehawks1942.s); must equal the
#                   shipped slave byte for byte
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot
VASMFLAGS ?=
SHIPPED ?= ../tmp/game/Battlehawks1942/Battlehawks1942.Slave

.PHONY: all original verify clean FORCE
all: Battlehawks1942.Slave

# Always assemble: options must not leave a stale variant. The vendored headers come first.
Battlehawks1942.Slave: Battlehawks1942.s FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym $(VASMFLAGS) -I. -Iinclude -I"$(NDK)" -o $@ $<

# -no-opt keeps every instruction encoded as written: the reconstruction must not let vasm
# re-choose encodings the shipped binary did not use.
original: FORCE
	$(VASM) -m68000 -pic -x -devpac -Fhunkexe -nosym -no-opt -Iinclude -I"$(NDK)" -o original/Battlehawks1942.Slave original/Battlehawks1942.s
	cmp original/Battlehawks1942.Slave $(SHIPPED) && echo "identical to the shipped slave"

verify:
	$(MAKE) Battlehawks1942.Slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1"

clean:
	rm -f Battlehawks1942.Slave original/Battlehawks1942.Slave
