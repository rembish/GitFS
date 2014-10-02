#!/usr/bin/env python2
# mUUID.py  -*- python -*-
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

import uuid

from gitfs.LockFile import LockFile


class mUUID(object):
    """UUID class to generate and work with UUIDs
    """
    @staticmethod
    def getUUIDFromFile(filename, create=False):
        uuid = mUUID()

        uuid.readFromFile(filename)
        if uuid.valid():
            return uuid

        lf = LockFile(filename + '.lock')
        try:
            lf.lock()
            uuid.readFromFile(filename)
            if uuid.valid():
                return uuid

            uuid = mUUID()
            uuid.generate()
            if not uuid.writeToFile(filename):
                return None
            return uuid
        finally:
            lf.unlock()

    def __init__(self):
        self.uuid = None

    def generate(self):
        self.uuid = uuid.uuid1()

    def readFromFile(self, filename):
        try:
            f = open(filename, 'r')
            for line in f:
                line = line.lstrip()
                if line[0] != '#':
                    break

            if len(line) > 0 and line[0] != '#':
                line = line.rstrip()
                self.uuid = uuid.UUID(line)
                return self

            return None

        except IOError:
            return None

    def writeToFile(self, filename):
        if self.uuid is None:
            return False

        try:
            f = open(filename, 'w')
            f.write(self.uuid.urn+'\n')
            f.close()
            return True
        except OSError:
            return False


    def toString(self):
        if self.uuid is None:
            return 'None'
        return self.uuid.hex

    def valid(self):
        if self.uuid is None:
            return False
        return True



