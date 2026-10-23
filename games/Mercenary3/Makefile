PYTHON ?= python3
BUILD ?= tmp/build
SHIPPED ?= tmp/game/Mercenary3_v1.2_0356/Mercenary3/Mercenary3.Slave
VASMFLAGS = -m68000 -x -devpac -Fhunkexe -nosym -no-opt

.PHONY: check original slave verify
check:
	$(PYTHON) tools/check_inputs.py

# Rebuild the shipped slave from its reconstruction and require identical bytes.
original:
	@mkdir -p "$(BUILD)"
	. amiga/env.sh && "$$VASM" $(VASMFLAGS) -I"$$WHDLOAD/Include" -I"$$NDK" \
	  -o "$(BUILD)/Mercenary3.original.Slave" whdload/original/Mercenary3.slave.asm
	cmp "$(BUILD)/Mercenary3.original.Slave" "$(SHIPPED)"
	@echo "original: identical to the shipped slave"

# The performance slave (whdload/Mercenary3.slave.asm) and its VERIFY build, which adds
# instruments. Both are always assembled so an option change never leaves a stale file.
slave:
	@mkdir -p "$(BUILD)"
	. amiga/env.sh && "$$VASM" $(VASMFLAGS) -I"$$WHDLOAD/Include" -I"$$NDK" \
	  -o "$(BUILD)/Mercenary3.Slave" whdload/Mercenary3.slave.asm

verify:
	@mkdir -p "$(BUILD)"
	. amiga/env.sh && "$$VASM" $(VASMFLAGS) -DVERIFY=1 -I"$$WHDLOAD/Include" -I"$$NDK" \
	  -o "$(BUILD)/Mercenary3.verify.Slave" whdload/Mercenary3.slave.asm

# Keep template-derived installer files and built slaves in ignored tmp/.
RELEASE ?= tmp/release-2.0
.PHONY: release
release: check original slave verify
	. amiga/env.sh && $(PYTHON) tools/build_release.py --slave "$(BUILD)/Mercenary3.Slave" "$(RELEASE)"
