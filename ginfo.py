#!/usr/bin/env python
# gsh.py  -*- python -*-
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
"""ginfo.py export a bunch of information about gitfs instances on the system
for use by shell commands.  In particular
    -r <id> gives the root of a mounted file system with a particular id.
"""

import logging

from sys import argv, stderr
from argparse import ArgumentParser

from GitFSClient import GitFSClient

def main(argv):
    parser = ArgumentParser(description='sync a local filesystem with the remote sourde.')
    cmdline = {}
    parser.add_argument('-r', '--find-root', action='append')
    
    cmdline = parser.parse_args(argv[1:])
    
    if 'find_root' in cmdline:
        for i in cmdline.find_root:
            c = GitFSClient.getClientByID(i)
            if c is not None:
                r = c.getMountPoint()
                if r is not None:
                    print '%s\n' %r

if __name__ == "__main__":
    main(argv)
