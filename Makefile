TARGET="ircstats"

dist: clean
	cp ircstats.py ${TARGET}
	cp CREDITS ${TARGET}
	cp COPYING ${TARGET}
	cp README ${TARGET}
	cp Makefile ${TARGET}

clean:
	rm -f *~ *.orig *.pyc
