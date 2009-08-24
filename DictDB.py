#!/usr/bin env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009 Joe Blaylock <jrbl@jrbl.org>
#           Portions copyright Raymond Hettinger
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.
"""Alternate DB based on a dict subclass

Runs like gdbm's fast mode (all writes all delayed until close).
While open, the whole dict is kept in memory.  Start-up and
close times are potentially long because the whole dict must be
read or written to disk.

Input file format is automatically discovered.
Output file format is selectable between pickle, json, yaml, and csv.
At least three are backed by fast C implementations.

Based on code from Raymond Hettinger, at 
http://code.activestate.com/recipes/576642/
"""

import pickle, json, csv
import os, sys, shutil
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

class DictDB(dict):

    def __init__(self, filename, flag=None, mode=None, format=None, verbose=False, *args, **kwds):
        self.flag = flag or 'c'             # r=readonly, c=create, or n=new
        self.mode = mode                    # None or octal triple like 0x666
        self.format = format or 'csv'       # csv, json, yaml, or pickle
        self.filename = filename
        self.verbose = verbose

        if (yaml == None) and (format == 'yaml'):
            sys.stderr.write("YAML requested but no YAML library installed, falling back to JSON.\n");
            sys.stderr.flush()

        if flag != 'n' and os.access(filename, os.R_OK):
            file = open(filename, 'rb')
            #file = codecs.open(filename, 'rb', encoding="utf-8")
            self._verbose("Reading %s data into memory... \n" % self.format)
            try:
                self.load(file)
            finally:
                file.close()
                self._verbose("...done.\n")
        self.update(*args, **kwds)

    def _verbose(self, notice):
        """Emits notice with a timestamp onto stderr, if verbose flag is set."""
        if self.verbose: 
           sys.stderr.write(unicode(datetime.now()) + ' ' + notice)
           sys.stderr.flush()

    def sync(self, altfile = None):
        if self.flag == 'r':
            return
        if altfile == None:
            filename = self.filename
        else:
            filename = altfile
        tempname = filename + '.tmp'
        file = open(tempname, 'wb')
        #file = codecs.open(tempname, 'wb', encoding="utf-8")
        self._verbose("Writing %s data to disk...\n" % self.format)
        try:
            self.dump(file)
        except Exception:
            file.close()
            os.remove(tempname)
            raise
        file.close()
        shutil.move(tempname, self.filename)    # atomic commit
        if self.mode is not None:
            os.chmod(self.filename, self.mode)
        self._verbose("...done.\n")

    def close(self):
        self.sync()

    def dump(self, file):
        if self.format == 'csv':
            csv.writer(file).writerows(self.iteritems())
        elif self.format == 'json':
            json.dump(self, file, separators=(',', ':'))
        elif self.format == 'yaml':
            yaml.dump(self, file, indent=4)
        elif self.format == 'pickle':
            pickle.dump(self.items(), file, -1)
        else:
            raise NotImplementedError('Unknown format: %r' % self.format)

    def load(self, file):
        # try formats from most restrictive to least restrictive
        for loader in (pickle.load, json.load, yaml.load, csv.reader):
            file.seek(0)
            try:
                return self.update(loader(file))
            except Exception:
                pass
        raise ValueError('File not in recognized format')


def dbopen(filename, flag=None, mode=None, format=None):
    return DictDB(filename, flag, mode, format)



if __name__ == '__main__':
    import random
    os.chdir('/dbm_sqlite/alt')
    print(os.getcwd())
    s = dbopen('tmp.shl', 'c', format='json')
    print(s, 'start')
    s['abc'] = '123'
    s['rand'] = random.randrange(10000)
    s.close()
    f = __builtins__.open('tmp.shl', 'rb')
    print (f.read())
    f.close()
