# Host cross-build of the Battlehawks 1942 slave.
#   make            WHDLoad 20.0 KickEmu slave (Battlehawks1942.s, vendored whdload/ + include/)
#   make verify     the same with VERIFY instruments (tape.s)
#   make c2pfull    VERIFY with the full-frame merge c2p experiment (c2p_full.s)
#   make tscale TSCALE=n  VERIFY with BH's step divisor T multiplied by n (tape.s);
#                   STICKREF=1 also divides the stick by the reference T 7
#   make original   Galahad's v1.0, reconstructed (original/Battlehawks1942.s); must equal the
#                   shipped slave byte for byte
WHDLOAD ?= $(HOME)/.local/share/amiga/WHDLoad-20.0
NDK ?= $(HOME)/.local/opt/m68k-amiga-elf/sys-include
VASM ?= $(HOME)/.local/vasmm68k_mot
VASMFLAGS ?=
SHIPPED ?= ../tmp/game/Battlehawks1942/Battlehawks1942.Slave

.PHONY: all original verify c2pfull tscale clean FORCE
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

c2pfull:
	$(MAKE) Battlehawks1942.Slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1 -DC2P_FULL=1"

tscale:
	$(MAKE) Battlehawks1942.Slave VASMFLAGS="$(VASMFLAGS) -DVERIFY=1 -DTSCALE=$(TSCALE) $(if $(STICKREF),-DSTICKREF=1)"

clean:
	rm -f Battlehawks1942.Slave original/Battlehawks1942.Slave
