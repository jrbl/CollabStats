#!/usr/bin env python
# -*- coding: utf-8 -*-
# Copyright (c) 2009 Raymond Hettinger
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
close time's are potentially long because the whole dict must be
read or written to disk.

Input file format is automatically discovered.
Output file format is selectable between pickle, json, and csv.
All three are backed by fast C implementations.

From Raymond Hettinger, at http://code.activestate.com/recipes/576642/
"""

import pickle, json, csv
import os, shutil

class DictDB(dict):

    def __init__(self, filename, flag=None, mode=None, format=None, *args, **kwds):
        self.flag = flag or 'c'             # r=readonly, c=create, or n=new
        self.mode = mode                    # None or octal triple like 0x666
        self.format = format or 'csv'       # csv, json, or pickle
        self.filename = filename
        if flag != 'n' and os.access(filename, os.R_OK):
            #file = __builtins__.open(filename, 'rb')
            file = open(filename, 'rb')
            try:
                self.load(file)
            finally:
                file.close()
        self.update(*args, **kwds)

    def sync(self):
        if self.flag == 'r':
            return
        filename = self.filename
        tempname = filename + '.tmp'
        #file = __builtins__.open(tempname, 'wb')
        file = open(tempname, 'wb')
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

    def close(self):
        self.sync()

    def dump(self, file):
        if self.format == 'csv':
            csv.writer(file).writerows(self.iteritems())
        elif self.format == 'json':
            json.dump(self, file, separators=(',', ':'))
        elif self.format == 'pickle':
            pickle.dump(self.items(), file, -1)
        else:
            raise NotImplementedError('Unknown format: %r' % self.format)

    def load(self, file):
        # try formats from most restrictive to least restrictive
        for loader in (pickle.load, json.load, csv.reader):
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
