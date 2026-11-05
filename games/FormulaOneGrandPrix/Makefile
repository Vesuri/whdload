include ../../common/mk/game.mk

# A build kept for a capture: make snapshot BUILD=verify OUT=tmp/c3/build-verify builds
# tmp/build/<BUILD>/ and copies it (slave, listing, build.json) to OUT, under tmp/.
.PHONY: snapshot ed check-disabled test-disabled
snapshot:
	@case "$(OUT)" in *..*) false ;; tmp/?*) true ;; *) false ;; esac || { echo "snapshot: OUT must be a directory under tmp/" >&2; exit 1; }
	@"$(COMMON)/build.sh" "$(or $(BUILD),release)"
	@mkdir -p "$(OUT)" && cp tmp/build/$(or $(BUILD),release)/* "$(OUT)/" && echo "copied to $(OUT)"

# F1GP-Ed 3.44 under Workbench on a writable copy of the game's data (tools/ed.sh).
ed:
	@tools/ed.sh

# B4: the disabled-options check on a capture, and its negative tests.
check-disabled:
	@python3 tools/check_disabled.py "$(CAPTURE)"
test-disabled:
	@python3 tools/test_disabled.py
