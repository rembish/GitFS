#!/usr/bin/env python
#
# Use Git as a Storage Filesystem
#
# Copyright (c) 2011 Sreejith K <sreejitemk@gmail.com>
# http://foobarnbaz.com
# Created on 11th Jan 2011
#

from __future__ import with_statement

from errno import EACCES
from sys import argv, exit
from time import time
import logging
import datetime
import os
from threading import Lock, Condition, Thread, Timer
from urlparse import urlparse # used to figure out the host so we can determine if it's remote or local.
from socket import getaddrinfo #call this to translate the host/port into something useable.
from ipy import IP # use to determine if we should consider the ip address local or not.

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

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

class GitRepo(object):

    def __init__(self, path, origin, branch, sync=False):
        self.path = path
        self.origin = origin
        self.branch = branch
        pr = urlparse(origin)
        host = pr.netloc
        host_port = host.partition(':');
        self.host = host_port[0]
        self.port = host_port[1]
        self.timer = None
        self.push_c = Condition()

        self.status = GitStatus(path)
        # sync all the files with git
        if sync:
            self.pull() # pulls first, so we can do a merge from other sources.
            self.synchronize()

    def synchronize(self):
        logging.debug('syncing')
        if self.syncNeeded():
            unstaged = self.status.unstagedFiles()
            for file in unstaged:
                self.stage(file)
            self.commit('syncing files @ %s' %datetime.datetime.now())
            self.push()

    def syncNeeded(self):
        return (self.status.stagedFiles() + self.status.unstagedFiles() and True or False)

    def stage(self, file):
        logging.debug('staging file %s' %file)
        os.system('git add %s' %file)

    def commit(self, msg):
        logging.debug('commiting file %s' %file)
        os.system('git commit -am \"%s\"' %msg)

    def pull(self):
        

    def push(self):
        logging.debug('pushing')
        self.push_c.aquire()
        ai = getaddrinfo(self.host, self.port)
        # for now assume private = rapid updates.
        if IP(ai[5]).isPrivate():
            push_time = 60
        else
            push_time = 600
            
        if time() - self.last_push > push_time:
            self.pull()
            try:
                self.status.clear() # Clear first
                ret = call('git push origin %s' %self.branch, shell=True)
            except OSError as e:
                ret = -1
            if ret == 0:
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = None
                self.last_push = time()
            else
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = None
                    
                #we need to check what happened and try again.
                self.status.update() 
                self.timer = Timer(60, self.push)
                
        self.push_c.release()

        
class GitFS(LoggingMixIn, Operations):
    """A simple filesystem using Git and FUSE.
    """
    def __init__(self, origin, branch='master', path='.'):
        self.origin = origin
        self.branch = branch
        self.root = os.path.realpath(path)
        self.repo = GitRepo(path, origin, branch, sync=True)
        self.halt = False
        self.rwlock = Lock()
        self.sync_c = Condition()
        self.sync_thread = Thread(target=self._sync, args=())
        self.sync_thread.start()
        self.timer = None

    def _sync(self):
        while True:
            self.sync_c.acquire()
            if not self.halt:
                # wait till a sync request comes
                self.sync_c.wait()
                if self.timer != None:
                    self.timer.cancel()
                    self.timer = None
                self.sync_c.release()
                self.repo.synchronize()
            else:
                self.sync_c.release()
                break

    def needSync(self):
        logging.debug('needSync()')
        self.sync_c.aquire()
        if self.timer == None:
            self.timer = Timer(60, self._sync, args=())
            self.timer.start()
        self.sync_c.release()
    
    def destroy(self, path):
        # stop sync thread
        self.sync_c.acquire()
        self.halt = True
        self.sync_c.notifyAll()
        self.sync_c.release()
    
    def __call__(self, op, path, *args):
        return super(GitFS, self).__call__(op, self.root + path, *args)
    
    def access(self, path, mode):
        if not os.access(path, mode):
            raise FuseOSError(EACCES)
    
    chmod = os.chmod
    chown = os.chown
    
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
                
    def getattr(self, path, fh=None):
        st = os.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
            'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))
    
    getxattr = None
    
    def link(self, target, source):
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
        return ['.', '..'] + os.listdir(path)

    readlink = os.readlink
    
    def release(self, path, fh):
        return os.close(fh)
        
    def rename(self, old, new):
        self.needSync()
        return os.rename(old, self.root + new)

    def rmdir(self, path):
        self.needSync()
        return os.rmdir(path)
    
    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))
    
    def symlink(self, target, source):
        return os.symlink(source, target)
    
    def truncate(self, path, length, fh=None):
        self.needSync()
        with open(path, 'r+') as f:
            f.truncate(length)
    
    unlink = os.unlink
    utimens = os.utime
    
    def write(self, path, data, offset, fh):
        self.needSync()
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.write(fh, data)
    

if __name__ == "__main__":
    if len(argv) != 5:
        print 'usage: %s <origin> <branch> <local_repo> <mount_point>' % argv[0]
        exit(1)
    fuse = FUSE(GitFS(argv[1], argv[2], argv[3]), argv[4], foreground=True)
