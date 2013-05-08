#!/usr/bin/env python
# GitFSClient.py  -*- python -*-
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
import errno
import time

from glob import iglob

from threading import Thread
from subprocess import call
from GitFSBase import GitFSBase, GitFSError

class GitFSClient(GitFSBase, object):
    @staticmethod
    def getClientByPath(path, recurse=True):
        """ Locate a client for a gitfs path. """
        path = os.path.realpath(os.path.abspath(path))

        while path != os.path.sep:
            logging.debug('getClientByPath: checking %s' %path)
            if os.path.ismount(path):
                logging.debug('%s is a mount point' %path)
                path = os.path.realpath(path)
                client = None

                #try:
                client = GitFSClient(path)
                #except GitFSError as ge:
                #   logging.debug('not a gitfs path: %s' %ge)
                #  pass
                
                if client is not None and client.pingRemote():
                    return client

            if not recurse:
                break
            
            path = os.path.abspath(os.path.join(path, os.pardir))

        raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs path.")

    @staticmethod
    def getClientByID(ident):
        base = GitFSBase()
        base.lockGitFSDir()
        try:
            client = GitFSClient.getClientByIDNoLock(ident)
        finally:
            base.unlockGitFSDir()
        return client

    @staticmethod
    def applyToIdents(ident, func, cleanup_on_exception=True):
        r = []
        if '.' not in ident:
            ident = ident + '.*'
        base = GitFSBase()
        csp = base.getControlSocketPath(ident)
        logging.debug('trying %s for ident %s' %(csp, ident))
        f = iglob(csp)
        
        for sockname in f:
            try:
                r.append(func(sockname))
            except Exception as e:
                logging.debug('apply to Idents caught %s' %e)
                if cleanup_on_exception:
                    try:
                        os.remove(sockname)
                    except OSError:
                        pass
        return r
            
    @staticmethod
    def getClientBySockName(sockname):
        base = GitFSBase()
        base.socket_path = sockname
        info = base.getInfoRemote()
        if 'path' in info:
            return GitFSClient(info['path'], sockname)
        raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs socket.")

    @staticmethod
    def checkSocketName(sockname):
        base = GitFSBase()
        base.socket_path = sockname
        info = base.getInfoRemote()
        logging.debug('attempting getinfo for %s returned %s' %(sockname, info))
        if 'path' in info:
            return sockname
        raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs socket.")

    @staticmethod
    def getClientByIDNoLock(ident):
        """ Locate a client based on it's id.  If it's mounted in
        mutiple places, only the first one found will be returned.
        Append the '.' followed by the pid to the id to request a
        specific client.
        """
        clients = GitFSClient.applyToIdents(ident, lambda s:GitFSClient.getClientBySockName(s) )
        if len(clients) > 0:
            return clients[0]
        return None

    def __init__(self, path, ident=None):
        super(GitFSClient, self).__init__()
        self.root = os.path.realpath(path)
        self.control_path = self.getControlDirectory()
        self.id = ident
            
        if self.getID() is None:
            raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs path.")

        if '.' not in self.getID():
            r = GitFSClient.applyToIdents(self.getID(), lambda s:GitFSClient.checkSocketName(s))
            if len(r) == 0:
                raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs path.")
            self.socket_path = r[0]
        else:
            self.socket_path = self.getControlSocketPath(self.getID())
        
        logging.debug("socket_path = %s" %self.socket_path)
        self.holdLock = False
        self.progressChecker = None

    def lockRemote(self):
        """Requests the other side lock the file system so that there
        is no modifications for a bit.  Only lasts for 60 seconds, but
        can be renewed indefinitely.
        """
        res = self.executeRemote({'action':'lock'})
        if res == None:
            return False
        try:
            return res['status'] == 'ok'
        except KeyError:
            return False

    def _lockRemoteAndHold(self):
        # XXXX Fixme:  Really need to use a lock and condition here.
        while self.holdLock:
            # if we are not making progress, then quit.
            if self.progressChecker != None and self.progressChecker.progress() != True:
                break
                
            self.lockRemote()
            time.sleep(30)
        
    def lockRemoteAndHold(self, progress=None):
        # XXXXX Fixme:  really need to lock this and single the
        # thread to exit using a Condition.
        self.holdLock=True
        self.progressChecker = progress
        t = Thread(target = self._lockRemoteAndHold, args=())
        t.daemon = True
        t.start()

    def renewLock(self):
        return self.lockRemote()

    def unlockRemote(self):
        self.holdLock=False
        res = self.executeRemote({'action': 'unlock'})
        if res == None:
            return False
        try:
            return res['status'] == 'ok'
        except KeyError:
            return False

    def pingRemote(self):
        res = self.executeRemote({'action': 'ping'})
        if res == None:
            return False
        try:
            return res['status'] == 'ok' and res['message'] == 'pong'
        except KeyError:
            return False

    def close(self):
        return

    def makeRootRelative(self, path):
        if path.startswith(self.root):
            return path[len(self.root):]
        raise GitFSError(GitFSError.eNotGitFS, "Not a gitfs path.")

    def getConfigForInstance(self, key):
        res = self.executeRemote({'action':'getConfig', 'key':key})
        logging.debug('getConfigForInstance(%s) got %s' %(key, res))
        if res is not None and key in res:
            return res[key]
        return None
        
    def sync(self):
        # now do the pull/push combination.
        # XXXXX Fixme: need a library to access git, not just shelling out.
        # this currently has to be done locally since
        # we are merging and we don't yet have a remote merge tool.
        # assumes it's run from beneath the git directory. 
        info = self.getInfoRemote();
        if 'origin' not in info:
            info['origin'] = 'origin'
        if 'branch' not in info:
            info['branch'] = 'master'

        self.lockRemoteAndHold()
        try:
            os.chdir(info['root'])
            # now do the pull/push combination.
            # XXXXX Fixme: need a library to access git, not just shelling out.
            call('git commit -a', shell=True)
            call('git pull \"%s\" \"%s\"' %(info['origin'], info['branch']), shell=True)
            call('git mergetool', shell=True)
            call('git commit -a', shell=True)
            call('git push \"%s\" \"%s\"' %(info['origin'], info['branch']), shell=True)
        
        finally:
            self.unlockRemote()

    def getID(self):
        if self.id is not None:
            return self.id
        
        mt = self.getMTab()
        if self.root not in mt:
            return None
        self.id = mt[self.root]
        return self.id

    def getMountPoint(self):
        return self.root
            

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(sys.argv) < 2:
        print 'usage: %s <local_repo> [command(s)]' %sys.argv[0]
        exit(1)
    client = GitFSClient(sys.argv[1])
    if len(sys.argv) == 2:
        if client.pingRemote():
            print "Pong\n"
            exit(0)
        else:
            print "No response.\n"
            exit(1)
    else:
        for command in sys.argv[2:]:
            res = client.executeRemote({'action': command})
            print "%s: %s" %(command, res)
    exit(0)
            
    
