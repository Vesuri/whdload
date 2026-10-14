.PHONY: help fetch verify prepare
help:
	@echo "fetch: download missing pinned inputs; verify: check archives; prepare: extract separate originals"
	@echo "reconstruct / verify-slave / render-slave / render-control / render-verify: new OUT below tmp; run / stop: project emulator"
fetch:
	@/bin/bash tools/inputs.sh fetch
verify:
	@/bin/bash tools/inputs.sh verify
prepare:
	@/bin/bash tools/inputs.sh prepare

.PHONY: reconstruct verify-slave render-slave render-control render-verify run stop
OUT ?= tmp/reconstructed
reconstruct:
	@/bin/bash -c '. amiga/env.sh; python3 tools/reconstruct.py --output "$(OUT)"'
verify-slave:
	@/bin/bash -c '. amiga/env.sh; python3 tools/reconstruct.py --verify --output "$(OUT)"'
render-slave:
	@/bin/bash -c '. amiga/env.sh; python3 tools/reconstruct.py --render --output "$(OUT)"'
render-control:
	@/bin/bash -c '. amiga/env.sh; python3 tools/reconstruct.py --render-control --output "$(OUT)"'
render-verify:
	@/bin/bash -c '. amiga/env.sh; python3 tools/reconstruct.py --render --render-verify --output "$(OUT)"'
run:
	@/bin/bash amiga/run.sh
stop:
	@/bin/bash amiga/run.sh stop

.PHONY: reconstruct-ocs check-ocs-reconstruction
reconstruct-ocs:
	@/bin/bash -c '. amiga/env.sh; python3 tools/ocs_reconstruct.py --output "$(OUT)"'
check-ocs-reconstruction:
	@/bin/bash -c '. amiga/env.sh; python3 tools/ocs_reconstruct_check.py --output "$(OUT)"'

.PHONY: check-ocs-display
check-ocs-display:
	@/bin/bash -c '. amiga/env.sh; python3 tools/ocs_display_check.py --output "$(OUT)"'
