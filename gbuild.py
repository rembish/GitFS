#!/usr/bin/env python2
# gbuild.py -*- python -*-
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
"""gbuild causes the local gfs to sync, and then runs gbuild on the remote
server to sync there and start the build.
"""

import logging
import os
import sys

from argparse import ArgumentParser
from sys import argv, exit
from subprocess import call
from GitFSClient import GitFSClient
from gsh import GSH

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    cwd = os.getcwd()
    client = GitFSClient.getClientByPath(cwd)
    info=client.getInfoRemote()
    logging.debug("received info: %s" %info)
    
    if 'origin' not in info:
        info['origin'] = 'origin'
    if 'branch' not in info:
        info['branch'] = 'master'
        
    client.sync()

    # Now, we need to run the remote version.
    host = client.getConfigForInstance('build_host')
    if host is None:
        host='localhost'
        
    command = client.getConfigForInstance('build_command')
    if command is None:
        command = 'make'

    command_args = [command ] + sys.argv[1:]
    # XXXX FXIME ned a way to massage the arguments before adding them to the command array.  Read something from the
    # config file and exec it.
    
    gsh = GSH(command)
    ssh = gsh.execute(host)
    ssh.displayAndWait()
