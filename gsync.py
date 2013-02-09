#!/usr/bin/env python
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
import os
import sys

from argparse import ArgumentParser
from sys import argv, exit
from subprocess import call
from GitFSClient import GitFSClient


if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    parser = ArgumentParser(description='sync a local filesystem with the remote sourde.')
    parser.add_argument('directory')
    
    cmdline = parser.parse_args(argv[1:])
    logging.debug('cmdline=%s' %cmdline)
    
    p, f = os.path.split(cmdline.directory)
    f = '.'+f
    d = os.path.join(p, f)
    os.chdir(d)

    client = GitFSClient(d)
    info=client.getInfoRemote()
    logging.debug("received info: %s" %info)
    
    if 'origin' not in info:
        info['origin'] = 'origin'
    if 'branch' not in info:
        info['branch'] = 'master'
        
    client.lockRemoteAndHold()

    try:
        # now do the pull/push combination.
        # XXXXX Fixme: need a library to access git, not just shelling out.
        call('git commit -a', shell=True)
        call('git pull \"%s\" \"%s\"' %(info['origin'], info['branch']), shell=True)
        call('git mergetool', shell=True)
        call('git commit -a', shell=True)
        call('git push \"%s\" \"%s\"' %(info['origin'], info['branch']), shell=True)
        
    finally:
        client.unlockRemote()
    
