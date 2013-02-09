#!/usr/bin/env python2
# gmount.py  -*- python -*-
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

"""gmount is a program to mount remote gitFS file systems.  It's
really a wrapper around GitFS.py to do such nice things as look in
/etc/gitfstab and ~/.gitfs/fstab to locate the file system and
parameters.  It assumes the shadow directory for any given directory
is the same one with a . prepended.  When there is a mkgitfs, it will
need to make sure all of the assumptions gmount and GitFS make are
respected.
"""

import GitFS
import os
import fuse
import logging
import sys
import platform

from argparse import ArgumentParser
from sys import argv, exit
from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


def readFSTab(file, fstab):
    logging.debug("reading fstab file: %s" %file)
    if not os.path.exists(file):
        return

    if not os.access(file, os.R_OK):
        print "%s not readable" %(file)
        return

    if os.path.isdir(file):
       map(lambda f: readFSTab(f, fstab), filter(lambda f: len(f) > 0 and f[len(f) - 1] != '~', os.path.listdir(file)))
       return
    
    lines = [line.strip() for line in open(file)]

    for l in lines:
        logging.debug("Looking at line %s" %l)
        try:
            l = l.strip()
            if len(l) == 0 or l[0] == '#':
                continue
            logging.debug("found non comment")
            d={}
            keys = ['device', 'mount_point', 'type', 'options', 'freq', 'passno']
            vals = l.split(None, 6)
            logging.debug("raw fstab entry: %s" %vals)
            for i in range(0,5):
                d[keys[i]] = vals[i]
            logging.debug('processed fstab entry: %s' %d)
            d['device'] = os.path.expandvars(os.path.expanduser(d['device']))
            d['mount_point'] = os.path.expandvars(os.path.expanduser(d['mount_point']))
            if d['type'] == 'gitfs':
                logging.debug("found gitfs file system.")
                ops = {}
                if d['options'] != 'none':
                    parseOptions(d['options'], ops)
                d['options'] = ops
                fstab.append(d)
                logging.debug("fstab entry: %s" %d)
            else:
                logging.debug('not a gitfs file system: %s' %d['type'])
        except Exception:
            pass

def parseOptions(o, options):
    # XXXX FIXME there should be a way to quote the ,'s
    strings = o.split(',')
    for s in strings:
        # s is either a single option or a name value pair.
        n, e, k = s.partition('=')
        if k != '':
            options[n] = k
        else:
            options[n] = True
            
def mergeCommandLineAndOptions(commandline, options):
    # command line overrides options. 'read_only', 'read_write',
    # 'volname' are the only command options that need to transfer
    if commandline.read_write and 'ro' in options:
        del options['ro']

    if commandline.read_only:
        options['ro'] = True

    if platform.system == 'Darwin' and commandline.volname != None:
        options['volname'] = commandline.volname

def mergeOptions(o1, o2):
    """Merge two sets of options.  things in o2 override things set in
    o1.  Changes are made to o1.  The goal is to take the global
    options in o2, and the local options specified in fstab.  The
    global options come from the commandline, so they override all the
    local ones.
    Currently the only option with special support is ro.
    """
    for k in o2.keys():
        o1[k] = o2[k]

    if 'ro' in o1 and ro not in o2:
        del o1[ro]

def mergeFSTab(fstabs):
    """Merge the options from a bunch of fstabs.  We have to check
    that both the device and the mount point are the same.  The
    calling code only checks that one of them is appropriate, but if
    there are conflicting fstab entries, we just throw an exception.
    """
    if len(fstabs) == 0:
        return fstabs

    fstab = fstabs[0]
    logging.debug('mergeFstab: first fstab: %s' %fstab)
    for fs in fstabs:
        if fs['mount_point'] != fstab['mount_point'] or fs['device'] != fstab['device']:
            raise GitFSExcpetion('Mismatched FSTab entries.')
        mergeOptions(fstab['options'], fs['options'])

    logging.debug('mergeFstab: final fstab: %s' %fstab)
    return fstab
    
def mount(device, mount_point, options):
    if platform.system == 'Darwin' and 'volname' not in options:
        dir, fil = os.path.split(mount_point)
        options['volname'] = fil
        
    origin = 'origin'
    if 'origin' in options:
        origin = options['origin']
        del options['origin']

    branch = 'master'
    if 'branch' in options:
        branch = options['branch']
        del options['branch']

    if 'verbose' in options:
        print ('mounting %s on %s with options %s' %(device, mount_point, options))

    if 'debug' not in options:
        logging.debug ('mounting %s on %s with options %s' %(device, mount_point, options))
        gitfs = GitFS.GitFS(origin, branch, device)
        try:
            fuse = FUSE(gitfs, mount_point, **options)
        finally:
            gitfs.destroy(None)

if __name__ == "__main__":
    #logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    parser = ArgumentParser(description='mount a GitFS file system')
    parser.add_argument('-a', '--auto', action = 'store_true', default = False)
    parser.add_argument('-d', '--debug', action = 'store_true', default = False)
    parser.add_argument('-f', '--force', action = 'store_true', default = False)
    parser.add_argument('-o', '--options', action = 'append', default = [])
    parser.add_argument('--read-only', '-r', '--read_only', action = 'store_true')
    parser.add_argument('-t', '--type')
    parser.add_argument('-u', '--update', action='store_true', default = False)
    parser.add_argument('-v', '--verbose', action='count', default = 0)
    parser.add_argument('--read-write', '-w', '--read_write', action='store_true', default = False)
    parser.add_argument('--fstab', action = 'append', default = [])
    parser.add_argument('--no-std-fstab','--no_std_fstab', action = 'store_true', default=False)
    parser.add_argument('--gitfs-dir', '--gitfs_dir')
    if platform.system == 'Darwin':
        parser.add_argument('--volname')
    parser.add_argument('device', nargs='?')
    parser.add_argument('mount_point', nargs='?')

    cmdline = parser.parse_args(argv[1:])

    logging.debug("cmdline=%s" %cmdline)

    if cmdline.type != None and cmdline.type != 'gitfs':
        print('gmount only supports gitfs.')
        exit(1)

    gitfsdir = '~/.gitfs'

    options={}
    # options will be a list of strings, separated by ,'s
    for o in cmdline.options:
        parseOptions(o, options)
                
    if cmdline.gitfs_dir != None:
        gitfsdir = cmdline.gitfs_dir
    else:
        if 'gitfsdir' in options:
            gitfsdir = options['gitfsdir']
        
    gitfsdir = os.path.expandvars(os.path.expanduser(gitfsdir))

    mergeCommandLineAndOptions(cmdline, options)

    if cmdline.device != None and cmdline.mount_point != None:
        mount(cmdline.device, cmdline.mount_point, options)
        exit(0)

    fstab=[]
    if not cmdline.no_std_fstab:
        for f in [ '/etc/fstab', os.path.join(gitfsdir, 'fstab') ]:
            readFSTab(f, fstab)

    for f in cmdline.fstab:
        readFSTab(f, fstab)

    if 'fstab' in options:
        for f in options[fstab].split(','):
            readFSTab(f, fstab)


    if cmdline.device == None:
        if not cmdline.auto:
            os.execv('/sbin/mount', ['mount']) # should not return.
            sys.exit(1)
    else:
        device = os.path.expandvars(os.path.expanduser(cmdline.device))
        fstab = mergeFSTab(filter(lambda f: f['device'] == device or f['mount_point'] == device, fstab))

    if len(fstab) == 0:
        print('Nomatch for %s in fstab.' %device)
        sys.exit(1)

    logging.debug("found fstab: %s" %fstab)
    mergeOptions(fstab['options'], options)
    if not cmdline.auto or 'noauto' not in fstab['options']:
        mount(fstab['device'], fstab['mount_point'], fstab['options'])
