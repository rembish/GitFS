#!/usr/bin/env python2
# ManyFile.py  -*- python -*-
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

import fileinput

from fileinput import FileInput

class ManyFile(object):
    """A generalized version of file input that allows for stopping
    reading the current file and switching to a different file.
    Reading the old file is resumed once the current file is complete.
    Useful for #include or similiar constructs.
    """

    def __init__(self, files=None, hook = None):
        self.fi = [] # an array of file input objects.  We push and pop onto this so we can resume.
        self.files = [] # an array of files that need to be read later.
        self.hook = None
        self.current = None # the current file input object.
        self.line = 0
        if files is not None:
            self.current = FileInput(files, openhook = self.hook)

    def include(self, files):
        if self.current is not None:
            self.fi.push(self.current)
        self.current = FileInput(files, openhook = self.hook)
            
    def fileno(self):
        if self.current is None:
            return None
        return self.current.fileno()

    def filename(self):
        if self.current is None:
            return None
        return self.current.filename()

    def lineno(self):
        return self.line

    def filelineno(self):
        if self.current is None:
            return None
        return self.current.filelineno()

    def isfirstline(self):
        if self.current is None:
            return None
        return self.current.isfirstline()

    def isstdin(self):
        return False

    def nextfile(self):
        if self.current is not None:
            self.current.nextfile()

    def close(self):
        if self.current:
            self.current.close()
        self.fi = []
        self.files = []

    def readline(self):
        if self.current is not None:
            l = self.current.readline()
            if len(l) > 0:
                self.line = self.line + 1
                return l

        # Advance to the next file
        if len (self.fi) > 0:
            self.current = self.fi.pop()
            return self.readline()

        # see if there are any files left to open
        if len (self.files) > 0:
            self.current = FileInput(self.files, openhook = fileinput.hook_compressed)
            self.files = []
            return self.readline()

        return ""

    def __getimem__ (self):
        return self.readline()

    def __iter__(self):
        return self

    def next(self):
        l = self.__getimem__()
        if l != '':
            return l
        raise StopIteration
