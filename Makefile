# GNU Makefile

CODE_BITS=ircstats DictDB.py UserStats.py UserTable.py validate_yaml user_merges ircColloquy.py
DIST_BITS=$(CODE_BITS) CREDITS COPYING README Makefile INSTALL
DIST_TARGET=dist_dir
LINT_OPTS=--max-line-length=120


help:
	@echo "check: check python files for errors"
	@echo "checkall: check python files for errors, warnings, or style problems"
	@echo "dist: copy important files only to a sub directory for easy packaging"
	@echo "clean: delete temporary file formats"

check:
	@for codefile in $(CODE_BITS); do \
		pylint ${LINT_OPTS} --errors-only $$codefile; \
	done

checkall:
	@for codefile in $(CODE_BITS); do \
		pylint ${LINT_OPTS} $$codefile; \
	done

dist: clean
	@for filename in $(DIST_BITS); do \
		cp -v $$filename $(DIST_TARGET); \
	done

clean:
	@rm -f *~ *.orig *.pyc *.bak
