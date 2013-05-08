#!/usr/bin/env python2
# ssh.py -*- python -*-
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

"""run commands on remote hosts via ssh and return an ssh object."""
import logging

from subprocess import Popen, PIPE
from sys import argv;

class SSH(object):
    def __init__(self, host, command):
        logging.debug('ssh %s:%s' %(host, command))
        self.host = host
        self.proc = None
        self.command = command
        self.ssh = "ssh"
        self.ssh_args = []

    def execute(self):
        c = [self.ssh] + self.ssh_args + [self.host] + self.command
        self.proc = Popen(c, bufsize = -1, stdin = PIPE, stdout=PIPE, stderr=PIPE, close_fds=True, shell=False)
        if self.proc.stdin:
            self.proc.stdin.close();
            self.proc.stdin = None

    def stdout(self):
        if self.proc is None:
            return None
        return self.proc.stdout

    def stderr(self):
        if self.proc is None:
            return None
        return self.proc.stderr
        
    def wait(self):
        if self.proc is None:
            return None
        return self.proc.wait()

    def poll(self):
        if self.proc is None:
            return None
        return self.proc.wait()
        
    def terminate():
        if self.proc is None:
            return None
        return self.proc.terminate();

    def kill():
        if self.proc is None:
            return None
        return self.proc.kill()

    def displayAndWait(self):
        print self.stdout().read()
        print self.stderr().read()

def main(host, command):
    ssh = SSH(host, [command])
    ssh.execute()
    print ssh.stdout().read()
    
    
if __name__ == "__main__":
    #logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(argv) != 3:
        print 'usage %s <host> <command>' % argv[0]
        exit(1)
    main (argv[1], argv[2])

