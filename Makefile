# The games are under games/<Game>; each has its own Makefile with the same targets, so
# `make run` inside games/F1GP equals `make run GAME=F1GP` here.
SHELL := /bin/bash
GAMES := $(patsubst games/%/game.conf,%,$(wildcard games/*/game.conf))
GAME_TARGETS := slave verify developer build run stop unpack record clean
# Paths given on the command line (SLAVE=, ARCHIVES=) are relative to this directory.
export CALLER_DIR := $(CURDIR)

.DEFAULT_GOAL := help
.PHONY: help list new check dist $(GAME_TARGETS)

help:
	@echo 'make list                       the games'
	@echo 'make <target> GAME=<Game>       slave verify developer build run stop unpack dist check record clean'
	@echo 'make dist | make check          every game (or GAME=<Game>); check also runs the repo checks'
	@echo 'make new GAME=<Game>            start a game from common/template'
	@echo 'Inside games/<Game>, the same targets without GAME=. Run options: common/run.sh.'

list:
	@for g in $(GAMES); do \
	  ( . games/$$g/game.conf; printf '%-20s %-32s %s\n' "$$g" "$${TITLE:-}" "$${VARIANTS:-}" ); \
	done

new:
	@[ -n "$(GAME)" ] || { echo 'make new GAME=<Game>' >&2; exit 1; }
	@common/new.sh "$(GAME)"

# Names the games when GAME is missing or unknown.
need_game = case " $(GAMES) " in *" $(GAME) "*) [ -n "$(GAME)" ] ;; *) false ;; esac || \
  { echo "make $@ GAME=<Game>; the games: $(GAMES)" >&2; exit 1; }

$(GAME_TARGETS):
	@$(need_game)
	@$(MAKE) --no-print-directory -C "games/$(GAME)" $@

dist:
	@$(if $(GAME),$(need_game);) set -e; for g in $(or $(GAME),$(GAMES)); do $(MAKE) --no-print-directory -C "games/$$g" dist; done

check:
	@$(if $(GAME),$(need_game);) common/check.sh repo
	@set -e; for g in $(or $(GAME),$(GAMES)); do $(MAKE) --no-print-directory -C "games/$$g" check; done
