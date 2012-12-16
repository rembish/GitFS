#!/usr/bin/env python
# GitFS.py -*- python -*-
# Use Git as a Storage Filesystem
#
# This work is
# Copyright (c) 2012 Ross Biro ross.biro@mindspring.com
#
# This work was derived from Sreejith K's gitfs.py with his original copyright notice preserved below
#
# This is Licensed under the GPL V3 with the exception that the below copyright notice must be maintained in
# all distributed versions of the source and that the accompanying license as describe in the file COPYING in the
# same directory of this file must be included as well.  For more complete terms of the GPL V3, see the file COPYING.GPL
# the requirements of both COPYING and COPYING.GPL must be met with the above mentioned exception.
#
# Sreejith's original work, from which this work is derived, is available on github, or see the link below.
#
# Original unmodified copyright notice:
#
# Copyright (c) 2011 Sreejith K <sreejitemk@gmail.com>
# Licensed under FreeBSD License. Refer COPYING for more information
#
# http://foobarnbaz.com
# Created on 11th Jan 2011
#
# End of original copyright notice.
#
# The main reason for using gitfs with shadow directories instead of just using git is that it makes it
# possible to maintain real git repositories inside of a git respository.  The escaping of filenames is
# critical for that.  It also allows the system to know when a file has been changed so that git commits only
# occur when something has changed.
# 
# Using this, git makes a good disconnected use file-system.  Eventually, we should be able to make it peer to peer
# using something like mdns so that collaboration can continue even when the main servers are down or a network is
# unreachable.
#

from __future__ import with_statement

from errno import EACCES, EBUSY
from sys import argv, exit
from time import time
import logging
import datetime
import os
import sys
import socket

from threading import Lock, Condition, Thread, Timer
from urlparse import urlparse # used to figure out the host so we can determine if it's remote or local.
from socket import getaddrinfo #call this to translate the host/port into something useable.
from IPy import IP # use to determine if we should consider the ip address local or not.
from subprocess import call, check_output

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
from SocketServer import ThreadingUnixStreamServer, BaseRequestHandler, ThreadingMixIn
from GitFSClient import GitFSClient, GitFSStringMixIn
#from EasyDialogs import AskYesNoCancel, Message
from Packetize import PacketizeMixIn

class GitStatus(object):

    def __init__(self, path):
        if not os.getcwd() == path:
            os.chdir(path)
        self.status = {}

    def update(self):
        self.clear()
        logging.debug('getting status')
        for line in os.popen('git status').readlines():
            line = line.strip()
            if line.startswith('#\t'):
                try:
                    status, file = [l.strip() for l in line[2:].split(':')]
                    if self.status.has_key(file):
                        self.status[status].append(file)
                    else:
                        self.status[status] = [file]
                except ValueError:
                    if self.status.has_key('untracked'):
                        self.status['untracked'].append( line[2:].strip() )
                    else:
                        self.status['untracked'] = [ line[2:].strip() ]
        logging.debug('current status: %r' %self.status)
        return self.status

    def stagedFiles(self):
        self.update()
        return self.status.get('renamed',  []) + \
               self.status.get('modified', []) + \
               self.status.get('new file', []) + \
               self.status.get('deleted',  [])

    def unstagedFiles(self):
        self.update()
        return self.status.get('untracked', [])

    def clear(self):
        self.status.clear()

class GitRepo(GitFSStringMixIn, LoggingMixIn, object):

    def __init__(self, path, origin, branch, sync=False):
        self.path = path
        logging.debug('repo.path = %s' %self.path)
        self.halt = False
        self.origin = origin
        self.branch = branch
        self.status = GitStatus(path)
        
        self.host = None
        self.merge_needed = 0
        self.push_c = Condition()
        self.forcePush()
        
        if sync:
            self.synchronize()

        # prime the push timer pump
        self.timer = Timer(0, self.push, args=())
        self.timer.start()

    def synchronize(self):
        logging.debug('syncing')
        if self.syncNeeded():
            unstaged = self.status.unstagedFiles()
            for file in unstaged:
                self.stage(file)
            self.commit('syncing files @ %s' %datetime.datetime.now())
            # Don't push here since a timer should already be
            # going and the push will happen when it should.


    def syncTime(self):
        if self.host == None or self.host == "":
            return 0

        # assume the system caches dns info, so we don't have to.
        ai = getaddrinfo(self.host, self.port)
            
        # for now assume private = rapid updates.
        for addressinfo in ai:
            if IP(addressinfo[4][0]).iptype == 'PRIVATE':
                return 60
            
        return 10*60

    def syncNeeded(self):
        return (self.status.stagedFiles() + self.status.unstagedFiles() and True or
                (time() - self.last_push > self.syncTime()))

    def stage(self, file):
        logging.debug('staging file %s' %file)
        call('git add \"%s\"' %self.escapeQuotes(file), shell=True)

    def commit(self, msg):
        logging.debug('commiting file %s' %file)
        call('git commit -am \"%s\"' %self.escapeQuotes(msg), shell=True)

    def forcePush(self):
        self.last_push = time() - 60*60*24*365

    def merge(self):
        logging.debug("merge required.")
        self.merge_needed = 1
        # ret = AskYesNoCancel('Merge required. Auto-Merge?', 0, 'OK', '', 'Cancel')

        # if ret == 1:
        #     ret = call('git pull --commit --no-progress origin \"%s\"' %self.branch, shell=True)
        #     if ret == 0:
        #         merge_needed = 0
        #     else:
        #         Message("Merge failed.  Please manually merge with gmerge")
            
        # else:
        #     Message("Please manually merge with gmerge")

    def pull(self):
        try:
            originurl = check_output('git remote show \"%s\" | grep Fetch' %self.origin, shell=True)
            originurl = originurl.partition(':')[2]
            originurl = originurl.rstrip().strip()

            if originurl == '':
                return 1
            
            logging.debug('originurl = %s' %originurl)
            pr = urlparse(originurl)
            host = pr.netloc
            if len(host) == 0:
                host = originurl
            self.host, colon, self.port = host.partition(':')
            self.port = 80
            logging.debug('repo.port = %s' %self.port)
            logging.debug('repo.host = %s' %self.host)

            if ('@' in self.host):
                logging.debug('found @ in %s' %self.host)
                self.host = self.host.partition('@')[2]

            logging.debug('pull')
            
            ret = call('git pull --ff-only origin \"%s\"' %self.branch, shell=True)
            if ret != 0:
                if self.merge_needed != 1:
                    self.merge()
            else:
                self.merge_needed = 0

            return 0
        
        except OSError as e:
            logging.debug('OSError')
            return 1

    def push(self):
        logging.debug('pushing')
        self.push_c.acquire()
        if self.halt:
            self.push_c.release()
            return
        
        push_time = self.syncTime()
        now = time()
        
        if now - self.last_push >= push_time:
            try:
                self.pull()
                self.status.clear() # Clear first
                ret = call('git push \"%s\" \"%s\"' %(self.origin, self.branch), shell=True)
            except OSError as e:
                ret = -1
            if ret == 0:
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = Timer(self.syncTime(), self.push, args=())
                    self.timer.start()
                self.last_push = time()
            else:
                if self.timer != None:
                    self.timer.cancel()
                    
                #we need to check what happened and try again.
                self.status.update() 
                self.timer = Timer(60, self.push, args=())
                self.timer.start()
        else:
            if self.timer != None:
                self.timer.cancel()
            self.timer = Timer(push_time - now + self.last_push, self.push, args=())
            self.timer.start()
            logging.debug('try to push again in %d seconds' %(push_time - now + self.last_push))
            
        self.push_c.release()

    def shutDown(self):
        logging.debug("repo shutdown")
        self.push_c.acquire()
        self.halt = True
        if self.timer != None:
            self.timer.cancel()
        self.timer = None
        self.push_c.release()

class GitFS(LoggingMixIn, GitFSStringMixIn, Operations):
    """A simple filesystem using Git and FUSE.
    """
    
    def __init__(self, origin, branch='master', path='.'):
        self.origin = origin
        self.branch = branch
        self.root = os.path.realpath(path)
        self.halt = False
        self.rwlock = Lock()
         # Can't use the default rlock here since we want to aquire/release from different threads
        self.sync_c = Condition(Lock())
        self.timer = None
        self.handlers = { 'ping': self._handlePing, 'lock': self._handleLock, 'unlock': self._handleUnlock }
        self.lock_timer = None
        self.lock_lock = Condition()
        self.locks = {}
        self.lock_expire_time = time()
        
        self.control_dir = self.getControlDirectory(self.root)
        try:
            os.mkdir(self.control_dir)
        except OSError:
            pass

        self.control_socket_path = self.getControlSocketPath(self.root)
        client = GitFSClient(self.root)

        try:
            if client.pingRemote():
                # There is another file system mounted.
                logging.debug("Exiting because file system already mounted.\n")
                raise FuseOSError(EBUSY)
        except socket.error as se:
            logging.debug("socket.error = %s" %se)
            pass

        client.close()
        client = None

        try:
            os.remove(self.control_socket_path)
        except OSError:
            pass
        self.control_server = None
        self.control_server = ThreadingUnixStreamServer(self.control_socket_path, type("GitFSRequestHandler",
                                                                              (PacketizeMixIn, BaseRequestHandler,object),
        dict(fs=self, dictFromString=self.parseDict, stringFromDict=self.marshalDict,
             handleDict=lambda s,d: s.fs._handleRequest(s,d))))
        self.control_server.daemon_threads = True

            # setup the threads last so that they don't prevent an exit.       
        self.control_thread = Thread(target = self.control_server.serve_forever, args=())
        self.control_thread.start()
        self.repo = GitRepo(path, origin, branch, sync=True)
        self.sync_thread = Thread(target=self._sync, args=())
        self.sync_thread.start()

    def _lockWithTimeOut(self, name, t):
        if t <= 0:
            return

        self.lock_lock.acquire()
        expt = t + time()
        self.locks[name] = expt
        if self.lock_expire_time - expt < 0:
            self.lock_expire_time = expt
            if self.lock_timer != None:
                self.lock_timer.cancel()
            else:
                logging.debug("Aquiring fresh lock")
                self.sync_c.acquire()
            self.lock_timer = Timer(t, self._lockTimerExpire, args=())
            self.lock_timer.start()
        self.lock_lock.release()

    def _lockTimerExpire(self):
        logging.debug('_lockTimeExpire')
        self.lock_lock.acquire()
        self.__lockTimerExpire()
        self.lock_lock.release()
        
    def __lockTimerExpire(self):
        logging.debug('__lockTimeExpire')
        now = time()
        t = now
        for key in self.locks:
            if t - self.locks[key] < 0:
                t = self.locks[key]
            if now - self.locks[key] > 300:
                del self.locks[key]

        if t - now > 0:
            self.lock_expire_time = t
            if self.lock_timer != None:
                self.lock_timer.cancel()
            else:
                logging.debug("***** ERROR ***** __lockTimerExpire doesn't have lock. acquiring")
                self.sync_c.aquire()
            self.lock_timer = Timer(t - now, self._lockTimerExpire, args=())
            self.lock_timer.start()
            logging.debug("extending lock.")
        else:
            if self.lock_timer != None:
                logging.debug("releasing lock.")
                self.lock_timer.cancel()
                self.lock_timer = None
                self.sync_c.release()

            
    def _unlock(self, name):
        if name not in self.locks:
            return

        self.lock_lock.acquire()
        t = self.locks[name]
        del self.locks[name]
        if t >= self.lock_expire_time or len(keys(self.locks)) == 0:
            self.__lockTimerExpire()
            
        self.lock_lock.release()
        
    def _handleRequest(self, request, d):
        if d['action'] in self.handlers:
            mf = self.handlers[d['action']]
            return mf(d, request)

        logging.debug("No request in packet: %s" %d)
        self._respondDict(request, {'status': 'Unknown Command'})
        return None

    def _respond(self, request, responseDict):
        request.sendDict(responseDict)

    def _handlePing(self, reqDict, request):
        self._respond(request, {'status': 'ok', 'message': 'pong' })

    def _handleLock(self, reqDict, request):
        self._lockWithTimeOut('%s' %request.request.fileno(), 60)
        self._respond(request, {'status': 'ok', 'name': '%s' %request.request.fileno()})

    def _handleUnlock(self, reqDict, request):
        self._unlock('%s' %request.request.fileno())
        self._respond(request, {'status': 'ok'})

    def _sync(self):
        while True:
            self.sync_c.acquire()
            if not self.halt:
                # wait till a sync request comes
                self.sync_c.wait()
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = None
                self.repo.synchronize()
                self.sync_c.release() # can't release this until sync is complete because we can't change files while we sync.
            else:
                self.repo.forcePush()
                self.repo.push()
                self.sync_c.release()
                break

    def forceSync(self):
        logging.debug('forceSync()')
        self.sync_c.acquire()
        self.sync_c.notifyAll()
        self.sync_c.release()
        
    def needSync(self):
        logging.debug('needSync()')
        self.sync_c.acquire()
        if self.timer == None:
            # save things once a minute so that we have snapshots
            self.timer = Timer(60, self.forceSync, args=())
            self.timer.start()
        self.sync_c.release()

    def shutdown(self):
        # stop sync thread
        self.sync_c.acquire()
        self.halt = True
        self.sync_c.notifyAll()
        self.sync_c.release()
        self.repo.shutDown()
    
    def destroy(self, path):
        self.shutdown()
        if self.control_server != None:
            self.control_server.shutdown()
            try:
                os.remove(self.control_socket_path)
            except OSError:
                pass
        
    def __call__(self, op, path, *args):
        path = self.escapePath(path)
        return super(GitFS, self).__call__(op, self.root + path, *args)
    
    def access(self, path, mode):
        if not os.access(path, mode):
            raise FuseOSError(EACCES)

    def chmod(self, path, mode):
        self.needSync()
        return os.chmod(path, mode)

    def chown(self, path, uid, gid):
        self.needSync()
        return super(GitFS, self).chown(path, uid, gid)
    
    def create(self, path, mode):
        return os.open(path, os.O_WRONLY | os.O_CREAT, mode)
    
    def flush(self, path, fh):
        self.sync_c.acquire()
        self.sync_c.notifyAll()
        self.sync_c.release()
        return os.fsync(fh)

    def fsync(self, path, datasync, fh):
        self.sync_c.acquire()
        self.sync_c.notifyAll()
        self.sync_c.release()
        return os.fsync(fh)

    def fsyncdir(self, path, datasync, fh):
        return self.fsync(path, datasync, fh)
                
    def getattr(self, path, fh=None):
        st = os.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
            'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
    
    getxattr = None
    
    def link(self, target, source):
        source = self.escapePath(source)
        self.needSync()
        return os.link(source, target)
    
    listxattr = None
    mkdir = os.mkdir
    mknod = os.mknod
    open = os.open
        
    def read(self, path, size, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.read(fh, size)

    def readdir(self, path, fh):
        files = os.listdir(path)
        uefiles = []
        for file in files:
            if self.isValidPath(file):
                uefiles = uefiles + [self.unescapePath(file)]
        return [ '.', '..'] + uefiles
    
    readlink = os.readlink
    
    def release(self, path, fh):
        return os.close(fh)
        
    def rename(self, old, new):
        self.needSync()
        return os.rename(old, self.root + self.escapePath(new))

    def rmdir(self, path):
        self.needSync()
        return os.rmdir(path)
    
    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))
    
    def symlink(self, target, source):
        self.needSync()
        return os.symlink(source, target)
    
    def truncate(self, path, length, fh=None):
        self.needSync()
        with open(path, 'r+') as f:
            f.truncate(length)

    def unlink(self, path):
        self.needSync()
        return os.unlink(path)
        
    utimens = os.utime
    
    def write(self, path, data, offset, fh):
        self.needSync()
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.write(fh, data)

def main(origin, branch, local, mountpt):
    dir, fil = os.path.split(mountpt)
    gitfs = GitFS(origin, branch, local);
    fuse = FUSE(gitfs, mountpt, foreground=True, volname=fil)
    gitfs.destroy(None)

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    if len(argv) != 5:
        print 'usage: %s <origin> <branch> <local_repo> <mount_point>' % argv[0]
        exit(1)
    main (argv[1], argv[2], argv[3], argv[4])

