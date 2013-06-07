#!/usr/bin/env python2
# GitFSBase.py  -*- python -*-
# Copyright (c) 2012-2013 Ross Biro
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
"""GitFSBase collects all the stuff that doesn't require a full client of filesystem,
but may be required for global access.  It also collects everything that is comment between
the filesytem and the client.  This includes things like lockGitFSDir and a couple of mixins.
"""

import os
import logging
import socket
import errno

from LockFile import LockFile
from ConfigFile import ConfigFile
from Packetize import PacketizeMixIn

class GitFSStringMixIn:
    """A collection of functions that manipulate strings and all the
    different components have to do in the same way.
    """
    def escapeQuotes(self, string):
        string.replace("\\", "\\\\")
        string.replace("\"", "\\\"")
        string.replace("$", "\\$")
        string.replace("`", "\\`")
        # XXXXXX FIXME: Make sure history is not enabled in subshell.  Don't depend on default.
        #string.replace("!", "\\!") # If history is enable, we may have problems.
        return string

    def escapePath(self, path):
        #logging.debug('escapePath(%s)' %path)
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
            if dict[key] is None:
                continue
            data = data + key + ':' + dict[key] + "\n"
        return data
    
    def getGitFSDir(self):
        path = os.path.expanduser('~/.gitfs')
        if not self.gitfs_dir_exists:
            try:
                os.makedirs(path)
                self.gitfs_dir_exists = True
            except OSError:
                pass
        return path
    
    def getControlDirectory(self):
        return os.path.join(self.getGitFSDir(),'control')

    def getInfoDirectory(self, root):
        return os.path.join(root, '@info')

    def getFullID(self, id):
        return "%s.%d" %(id, os.getpid())

    def getControlSocketPath(self, id, server=False):
        if self.control_socket_path is not None:
            return self.control_socket_path
        if server:
            id = self.getFullID(id)
        if id is None:
            id = ''
            
        return os.path.join(self.getControlDirectory(), id)

    def getUUIDFile(self, root):
        return os.path.join(self.getInfoDirectory(root), 'uuid')
        
    def checkDict(self, dict, **kwargs):
        c = dict(**kwargs)
        try:
            for key in c:
                if dict[key] != c[key]:
                    return False
            return True
        except KeyError:
            return False

class GitFSError(Exception):
    """Errors that gitfs can throw."""
    eNotGitFS = 1
    
class GitFSBase(PacketizeMixIn, GitFSStringMixIn, object):
    def __init__(self):
        self.socket = None
        self.config = None
        self.control_socket_path = None
        self.stringFromDict=self.marshalDict
        self.dictFromString=self.parseDict
        self.gitfs_dir_exists = False # really just means unknown
        self._length_bytes = 2
        self.packet=[]
        # priorities are from least to greatest.
        self.config_file_priorities={'default': [ 'filesystem', 'system', 'gitfsdir' ],
                                     'build_host': [ 'system', 'filesystem', 'gitfsdir' ],
                                     'build_command': [ 'system', 'filesystem', 'gitfsdir' ],
                                     }
        self.config_files={ 'gitfsdir': '${GITFSDIR}/config',
                            'system': '/etc/gitfs/config',
                            'filesystem': '${GITFSROOT}/@gitfs/config',
                            }

    def getConfigFileName(self, name):
        if name not in self.config_files:
            logging.debug('config_files %s=%s' %(name, self.config_files[name]))
            return None
        path = self.config_files[name]
        os.environ['GITFSDIR'] = self.getGitFSDir()
        path = os.path.expandvars(path)
        path = os.path.expanduser(path)
        return path

    def lockGitFSDir(self):
        dir = self.getGitFSDir();
        self.git_fs_dir_lock = LockFile(os.path.join(dir, 'directory_lock'))
        self.git_fs_dir_lock.lock();

    def getMTabFileName(self):
        return os.path.join(self.getGitFSDir(), 'mtab')

    def getMTab(self, lock=True):
        cf = ConfigFile()
        if lock:
            self.lockGitFSDir()
        try:
            cf.readFile(self.getMTabFileName())
        except IOError:
            pass
        finally:
            if lock:
                self.unlockGitFSDir()
        logging.debug('read configuration: %s\n' %cf.getConfig())
        return cf.getConfig()

    def updateMTab(self, mtab):
        cf = ConfigFile()
        cf.setConfig(mtab)
        self.lockGitFSDir()
        try:
            cf.writeFile(self.getMTabFileName())
        finally:
            self.unlockGitFSDir()

    def getConfig(self, name):
        if self.config is not None and name in self.config:
            return self.config[name]
        cf = ConfigFile()
        files = []
        f = self.getConfigFileName(name)
        logging.debug('getConfig filename for %s is %s' %(name, f))
        if f is None:
            return None
        files.append(f)
        if name == 'gitfsdir':
            self.lockGitFSDir()
        try:
            cf.readFile(files)
        except IOError:
            # ignore files that don't exist and the like.
            pass
        finally:
            if name == 'gitfsdir':
                self.unlockGitFSDir()
        self.config = cf.getConfig()
        return self.config

    def flushConfig(self):
        self.config = None

    def unlockGitFSDir(self):
        self.git_fs_dir_lock.unlock()
        self.git_fs_dir_lock = None

    def _sendDict(self, dict):
        if self.socket == None:
            logging.debug('need to create new socket to connect to %s' %self.socket_path)
            if not os.path.exists(self.socket_path):
                logging.debug('socket %s doesn\'t exist' %self.socket_path)
                raise socket.error("Socket Not Found")
            logging.debug('about to create unix socket')
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            logging.debug('new socket = %s' %self.socket)
            logging.debug('about to connect.')
            self.socket.connect(self.socket_path)
            logging.debug('setting timeout.')
            self.socket.settimeout(2)
            self.request = self.socket
        self.sendDict(dict)

    def _recvDict(self):
        self.getPacket()
        if len(self.packet) == 0:
            return None
        dict = self.packet[0]
        self.packet=[]
        logging.debug('_recvDict returning %s' %dict)
        return dict

    def handleDict(self, dict):
        self.packet.append(dict)

    def executeRemote(self, dict):
        while True:
            try:
                self._sendDict(dict)
                dict = self._recvDict()
                return dict
            except socket.timeout as to:
                logging.debug('socket timeout')
                self.socket = None
                return None
            except socket.error as so:
                logging.debug("socket error so=%s" %so)
                self.socket = None
                if so.errno != errno.EPIPE:
                    raise so

    def getInfoRemote(self):
        res = self.executeRemote({'action': 'info'})
        if res == None:
            return {}
        try:
            if res['status'] != 'ok':
                return {}
            return res
        except KeyError:
            return {}

