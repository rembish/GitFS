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
"""GSH calls gsync, and then usses ssh to run a command on the remote machine.
It should have identical systax as ssh since all it does is call gsync locally,
then ssh to the remote machine, cd to the same directory relative to the gitfs mount,
run gsync, and finally run the remote command.
"""
import os

from GitFSClient import GitFSClient
from ssh import SSH

class GSH:
    "The main class.  First you build it, then you tweak it, then you execute it."

    def __init__(self, command, path=os.getcwd()):
        self.command = command;
        path = os.path.realpath(os.path.abspath(path))
        self.client = GitFSClient.getClientByPath(path)
        self.path = self.client.makeRootRelative(path)
        if self.path is None or self.path == '':
            self.path = '.'

    def execute(self, host):
        """Actually execute the command on host."""
        #The command has to be cd `find-path` && gsync && command
        self.client.sync()
        ssh_command = "cd `ginfo.py -r \"%s\"` && gsync.py . && cd %s && %s" %(self.client.getID(), self.path, self.command)
        myssh = SSH(host, [ "/bin/sh", "-c", ssh_command ]);
        myssh.execute()
        return myssh;

    
    
