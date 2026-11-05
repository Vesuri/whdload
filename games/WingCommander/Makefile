include ../../common/mk/game.mk

# The OCS reconstruction and display checks (docs/development.md); OUT is a new directory
# below tmp/.
.PHONY: check-ocs-reconstruction check-ocs-display
OUT ?= tmp/checks/$@
check-ocs-reconstruction:
	@/bin/bash -c '. ../../common/env.sh; python3 tools/ocs_reconstruct_check.py --output "$(OUT)"'
check-ocs-display:
	@/bin/bash -c '. ../../common/env.sh; python3 tools/ocs_display_check.py --output "$(OUT)"'
