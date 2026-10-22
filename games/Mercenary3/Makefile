PYTHON ?= python3
BUILD ?= tmp/build
SHIPPED ?= tmp/game/Mercenary3_v1.2_0356/Mercenary3/Mercenary3.Slave
VASMFLAGS = -m68000 -x -devpac -Fhunkexe -nosym -no-opt

.PHONY: check original
check:
	$(PYTHON) tools/check_inputs.py

# Rebuild the shipped slave from its reconstruction and require identical bytes.
original:
	@mkdir -p "$(BUILD)"
	. amiga/env.sh && "$$VASM" $(VASMFLAGS) -I"$$WHDLOAD/Include" -I"$$NDK" \
	  -o "$(BUILD)/Mercenary3.original.Slave" whdload/original/Mercenary3.slave.asm
	cmp "$(BUILD)/Mercenary3.original.Slave" "$(SHIPPED)"
	@echo "original: identical to the shipped slave"
