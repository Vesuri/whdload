include ../../common/mk/game.mk

# Rebuild the shipped 1.2 slave from src/original/ (the Mercenary3-original variant) and
# require it to equal the installed one byte for byte (game.sh game_original).
.PHONY: original
original:
	@bash -c 'set -euo pipefail; . "$(COMMON)/lib.sh"; load_game; game_original'
