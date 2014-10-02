#!/usr/bin/env python2
# gmkfs.py  -*- python -*-
# Copyright (c) 2012 Ross Biro
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
"""gsync grabs a lock on the filesystem, then does a pull/push.  This syncs the local to the remote.  Useful before
intiating a remote build.
"""

import logging
from argparse import ArgumentParser
from sys import argv, stderr

from gitfs.GitFSClient import GitFSClient

if __name__ == "__main__":
    logging.basicConfig(stream=stderr, level=logging.DEBUG)
    parser = ArgumentParser(description='sync a local filesystem with the remote sourde.')
    parser.add_argument('directory')

    cmdline = parser.parse_args(argv[1:])
    logging.debug('cmdline=%s' %cmdline)

    client = GitFSClient.getClientByPath(cmdline.directory)
    client.sync()

