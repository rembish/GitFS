#!/usr/bin/env python
# GFile.py  -*- python -*-
# Copyright (c) 2013 Ross Biro
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#

"""GFile implements a file like object that allows for putting bi-directional filters
into the stream to modify the input/output, similiar to unix shell pipes.
"""

import os

class GFile(object):
    @staticmethod
    def open(name, mode='r', buffering=-1):
        return GFile(open(name, mode, buffering))
        
    def __init__(self, f):
        self.closed = False
        self.encoding = None
        self.errors = None
        self.mode = None
        self.name = None
        self.newlines = None
        self.softspace = 0
        self.file = f

    def close(self):
        self.file.close()

    def flush(self):
        self.file.flush()

    def fileno(self):
        return self.file.fileno()

    def isatty(self):
        return self.file.isatty()

    def next(self):
        l = self.readline()
        if l != '':
            return l
        raise StopIteration

    def read(self, size=None):
        return self.file.read(size)

    def readline(self, size=None):
        return self.file.readline(size)

    def readlines(self, sizehint=None):
        return self.file.readlines(sizehint)

    def seek(self, offset, whence=os.SEEK_SET):
        return self.file.seek(offset, whence)

    def tell(self):
        return self.file.tell()

    def truncate(self):
        return self.file.truncate()

    def write(self, str):
        return self.file.write(str)

    def writelines(self, seq):
        return self.file.writelines(seq)

    def writeln(self, str):
        return self.file.write(str+'\n')
