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
"""gmkfs creates a Git filesystem.  In particular it creates a shadow
directory, runs git init, remote, and pull.
"""

import logging
import sys
import os

from argparse import ArgumentParser
from sys import argv, exit
from subprocess import call

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    parser = ArgumentParser(description='create the shadow directory for a GitFS file system')
    parser.add_argument('--origin', default='origin')
    parser.add_argument('--branch', default='master')
    parser.add_argument('--no_fstab', '--no-fstab', action='store_true', default=False)
    parser.add_argument('--gitfs-dir', '--gitfs_dir', default='~/.gitfs')
    parser.add_argument('remote')
    parser.add_argument('directory')

    cmdline = parser.parse_args(argv[1:])
    logging.debug('cmdline=%s' %cmdline)
    p, f = os.path.split(cmdline.directory)
    f = '.'+f
    d = os.path.join(p, f)
    r = cmdline.remote
    o = cmdline.origin
    b = cmdline.branch
    gitfsdir = os.path.expandvars(os.path.expanduser(cmdline.gitfs_dir))
    try:
        os.mkdir(d)
    except OSError:
        pass

    os.chdir(d)
    call('git init', shell=True)
    call('git remote add -t %s %s "%s"' %(b, o, r), shell=True)
    call('git pull %s' %(o), shell=True)
    if cmdline.no_fstab == False:
        try:
            os.mkdir(gitfsdir)
        except OSError:
            pass
        try:
            options="origin=%s" %o
            open(os.path.join(gitfsdir, 'fstab'), 'a').write('{:<23} {:<24} {:<7} {:<15} 0 0\n'.format(d,
                                                                                                       cmdline.directory,
                                                                                                       'gitfs', options))
        except OSError:
            pass
        
    
    
