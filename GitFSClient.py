#!/usr/bin/env python
#
# GitFSClient.py  -*- python -*-
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

"""GitFSClient

This module exports the classes used to communicate with the GitFS
file system module.  Currently the main thing it does is test to see
if a filesystem base directory is currently mounted (and the FUSE
module is alive) and to lock the file system so that auxillary code
can perform operations like complex merges.

The primary class that is exported is GitFSSClient.

"""
import socket
import os
import sys
import logging

class GitFSStringMixin:
    """A collection of functions that manipulate strings and all the
    different components have to do in the same way.
    """
    
    def escapeQuotes(self, string):
        string.replace("\\", "\\\\")
        string.replace("\"", "\\\"")
        string.replace("$", "\\$")
        string.replace("`", "\\`")
        #string.replace("!", "\\!") # If history is enable, we may have problems.
        return string

    def escapePath(self, path):
        logging.debug('escapePath(%s)' %path)
        if path == '/' or path == '':
            return path
        dir, fil = os.path.split(path)

        if fil != '.' and fil != '..' and len(fil) > 0 and fil[0] in '@._':
            fil = '@' + fil
        return os.path.join(self.escapePath(dir), fil)

    def unescapePath(self, path):
        logging.debug('unescapePath(%s)' %path)
        if path == '/' or path == '':
            return path
        dir, fil = os.path.split(path)

        if fil != '.' and fil != '..' and len(fil) > 0 and fil[0] == '@':
            fil = fil[1:]
            
        return os.path.join(self.unescapePath(dir), fil)

    def isValidPath(self, path):
        if path == '/' or path == '':
            return True

        dir, fil = os.path.split(path)
        
        if fil != '.' and fil != '..' and len(fil) > 0:
            if fil[0] == '.':
                return False
            if fil[0] == '@' and (len(fil) < 2 or not fil[1] in '@._') :
                return False

        return self.isValidPath(dir)

    def parseDict(self, data):
        dict = {}
        for line in data.splitlines():
            line.strip()
            if line != '':
                key, colon, value = line.partition(':')
                dict[key] = value
            # endif
        # end for
        return dict

    def marshalDict(self, dict):
        data=''
        for key in dict.keys():
            data = data + key + ':' + dict[key] + "\n"
        return data

    def getControlDirectory(self, root):
        return root+'/@gitfs'

    def getControlSocketPath(self, root):
        return self.getControlDirectory(root) + '/control'



class GitFSClient(GitFSStringMixin, object):

    def __init__(self, path):
        self.socket = None
        self.root = os.path.realpath(path)
        self.control_path = self.getControlDirectory(self.root)
        self.socket_path = self.getControlSocketPath(self.root)
        logging.debug("socket_path = %s" %self.socket_path)

    def _sendDict(self, dict):
        if self.socket == None:
            if not os.path.exists(self.socket_path):
                raise socket.error("Socket Not Found")
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.socket.connect(self.socket_path)
            self.socket.settimeout(2)
        data = self.marshalDict(dict)
        self.socket.send(data)

    def _recvDict(self):
        data = self.socket.recv(4096)
        return self.parseDict(data)
    
    def executeRemote(self, dict):
        while True:
            self._sendDict(dict)
            try:
                dict = self._recvDict()
                return dict
            except socket.timeout as to:
                pass
    

    def lockRemote(self):
        """Requests the other side lock the file system so that there
        is no modifications for a bit.  Only lasts for 60 seconds, but
        can be renewed indefinitely.
        """
        res = self.executeRemote({'action':'lock'})
        return res['status'] == 'ok'

    def renewLock(self):
        return self.lockRemote()

    def unlockRemote(self):
        res = self.executeRemote({'action': 'unlock'})
        return res['status'] == 'ok'

    def pingRemote(self):
        res = self.executeRemote({'action': 'ping'})
        return res['status'] == 'ok' and res['message'] == 'pong'

    def close(self):
        return

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) != 2:
        print 'usage: %s <local_repo>' %sys.argv[0]
        exit(1)
    client = GitFSClient(sys.argv[1])
    if client.pingRemote():
        print "Pong\n"
        exit(0)
    print "No response.\n"
    exit(1)
    
