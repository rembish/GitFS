#!/usr/bin/env python2
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
import fcntl
import errno
import os
import logging
import sys
import subprocess
from sys import argv, exit
from argparse import ArgumentParser

from GitFSClient import GitFSClient
from gitfs.ssh import SSH


class GSH:
    "The main class.  First you build it, then you tweak it, then you execute it."

    def __init__(self, command, path=os.getcwd()):
        self.command = command
        path = os.path.realpath(os.path.abspath(path))
        self.client = GitFSClient.getClientByPath(path)
        self.path = self.client.makeRootRelative(path)
        if self.path is None or self.path == '':
            self.path = '.'

    def execute(self, host):
        """Actually execute the command on host."""
        #The command has to be cd `find-path` && gsync && command
        self.client.sync()
        #ssh_command = "cd `ginfo.py -r \"%s\"` && gsync.py . && cd %s && %s" %(self.client.getID(), self.path, self.command)
        ssh_command = 'gsh.py --remote --id \"%s\" --path \"%s\" --command \"%s\"' %(self.client.getID(), self.path, self.command)
        self.ssh = SSH(host, [ ssh_command ])
        self.ssh.execute()

    def setNonBlocking(self):
        fcntl.fcntl(self.stderr(), fcntl.F_SETFL, os.O_NDELAY)
        fcntl.fcntl(self.stdout(), fcntl.F_SETFL, os.O_NDELAY)
        fcntl.fcntl(self.stdin(), fcntl.F_SETFL, os.O_NDELAY)

    def pollInfo(self):
        """returns a dict of names: (fileno, read, write, error, ...) tuples.
        names are only used to pass back into the handler for read/write/errors.
        Anything after the 4th entry in the tuple is ignored.  The whole return from
        this function is passed back in, so extra information can be stashed all over the
        place.
        """
        return { 'stdout': [ self.ssh.stdin(), False, len(self.out_buffer) > 0, True ],
                'stdin' : [ self.ssh.stdout(),  len(self.in_buffer) < self.buffer_max, False, True ],
                'stderr': [ self.ssh.stderr(),  len(self.err_buffer) < self.buffer_max, False, True ]
                }

    def pollHit(self, name, res):
        if name == 'stdout':
            self.readStdout()
        elif name == 'stdin':
            self.writeStdin()
        elif name == 'stderr':
            self.readStderr()

    def _read(self, file, size):
        try:
            buff = file.read(size)
        except IOError as ioe:
            if ioe.errno != errno.EAGAIN and ioe.errno != errno.EWOULDBLOCK:
                raise ioe
            buff = ''
        return buff

    def _write(self, file, buffer):
        try:
            ret = file.write(buffer)
        except IOError as ioe:
            if ioe.errno != errno.EAGAIN and ioe.errno != errno.EWOULDBLOCK:
                raise ioe
            ret = 0
        return ret

    def readStdin(self):
        buff = self._read(self.stdin(), self.max_in_buff - len(self.in_buffer) )
        self.in_buffer.append(buff)
        for f in self.stdin_call_backs:
            f(self)

    def readStdout(self):
        buff = self._read(self.stdout(), self.max_out_buff - len(self.out_buffer) )
        self.out_buffer.append(buff)
        for f in self.stdout_call_backs:
            f(self)

    def readStderr(self):
        buff = self._read(self.stderr(), self.max_err_buff - len(self.err_buffer) )
        self.err_buffer.append(buff)
        for f in self.stderr_call_backs:
            f(self)

    def writeStdIn(self):
        if len(self.in_buff) > 0:
            w = self._write(self.stdin(), self.in_buff)
            if w > 0:
                self.in_buff = self.in_buff[w:]
                for f in self.stdin_call_backs:
                    f(self)

    def stdout(self):
        if self.ssh is None:
            return None
        return self.ssh.stdout()

    def stderr(self):
        if self.ssh is None:
            return None
        return self.ssh.stderr()

    def stderr(self):
        if self.ssh is None:
            return None
        return self.ssh.stderr()

    def read(self):
        return self.stdout().read()

    def write(self, buff):
        return self.stdin().write(buff)

    def readerr(self):
        return self.stderr().read()

    def displayAndWait(self):
        if self.ssh is not None:
            self.ssh.displayAndWait()

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

    parser = ArgumentParser(description='execute ')
    parser.add_argument('-r', '--remote', action='store_true', default = False)
    parser.add_argument('-p', '--path')
    parser.add_argument('-i', '--id')
    parser.add_argument('-c', '--command')
    cmdline = parser.parse_args(argv[1:])

    if cmdline.remote:
        client = GitFSClient.getClientByID(cmdline.id)
        if client is None:
            print >> sys.stderr, 'Unable to locate gitfs file system %s' %cmdline.id
            exit(1)

        os.chdir(os.path.join(client.getMountPoint(), cmdline.path))
        client.sync()
        subprocess.call(cmdline.command, shell=True)
        exit(0)







