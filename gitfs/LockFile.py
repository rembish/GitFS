# LockFile.py  -*- python -*-
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
""" Atomically create a lockfile and store the current hostname and
process pid in it.  Stale lockfiles will be removed the next time
someone on the same host tries to get the lock and sees that the pid
is no longer valid.

This works by first creating <lockfile>.host.pid for the current process.
Then it checks for the existance of any other files with the same format.
If it finds one, it removes it's lock file, pauses for a random amount of
time, and then tries again.

Once it is convinced that there are no other <lockfile>.host.pid
around, it attempts to read <lockfile>.  If <lockfile> exists, then it
reads the contents which should be of the form host::pid.  If host
does not match the current name, it assumes that someone else has the
lock, waits a bit and tries again.

If the hostname does match, it checks to see if the pid exists.  If it
does not, then it assumes that the lockfile is stale and takes
ownership of the lockfile by writing its hostname::pid into it.

If the lockfile didn't exist in the first place, then it is created
and the current process takes ownership.

This will fail with network file systems that do not have unique hostnames
or if the network filesystem has a local cache that does not get invalidated
when another machine flushes a new file.

A good extension would be to create a pid service so that hostname::pid could
be validated even if hostname did not match.

The filesystem must support mtime, or at least return mtime of current
time, or the temporary lock cleanupcode will break everything.
"""

import os
import errno
import logging
import socket

from time import time, sleep
from glob import iglob
from random import random
from stat import ST_MTIME


class LockFile(object):
    @staticmethod
    def pid_exists(pid):
        """Check if a pid exists"""
        if pid < 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                return False
        return True

    def __init__(self, path):
        """ path should be the path of the lockfile that will be created in the end.
        """
        self.path = path
        self.temp_lock_life = 5*60 # 5 minutes

    def cleanupLocks(self):
        """ Get rid of any temprorary lock files if they are more than
        twice as old as we allow them to be."""
        locks = iglob(self.path + '.*')
        for f in locks:
            try:
                s = os.stat(f)
                if time() - ST_MTIME(s) > 2*self.temp_lock_life:
                    os.remove(f)
            except OSError:
                pass

    def lock(self, timeout = None):
        """ timeout should be the number of seconds to try before giving up
        and returning false. 0 means try and give up write away.  None
        means never give up."""
        start_time = time()
        my_lock_file = self.path + '.%s.%s' %(socket.gethostname(), os.getpid())
        my_glob = self.path + '.*'
        done = False
        while not done:
            try:
                lock_create_time=time()
                f = open(my_lock_file, 'w+b', 0)
                f.write('%s\n' %(os.getpid()))
                f.flush()
                os.fsync(f.fileno())
                f.close()
                lock_files = iglob(my_glob)

                try:
                    lf = next(lock_files)
                    lf = next(lock_files)
                    print "Too Many lock files.\n"
                    continue
                except StopIteration:
                    pass

                if time() - lock_create_time > self.temp_lock_life:
                    print "lock file too old.\n"
                    continue

                if (os.path.exists(self.path)):
                    f = open (self.path, 'rb')
                    host_pid = f.readline()
                    f.close()
                    host, pid = host_pid.split('::')
                    if host == socket.gethostname():
                        pid = int(pid)
                        if pid == os.getpid():
                            raise Exception("Attempt to relock lockfile")
                        if self.processIsAlive(pid):
                            print "Someone else has the lock.\n"
                            continue
                        try:
                            os.remove(self.path)
                        except OSError:
                            pass
                f = open (self.path, 'w+b')
                f.write('%s::%s\n' %(socket.gethostname(), os.getpid()))
                f.flush()
                os.fsync(f.fileno())
                f.close()
                done = True
                return True
            finally:
                try:
                    os.remove(my_lock_file)
                except OSError:
                    pass
                if not done:
                    print "Not done"
                    self.cleanupLocks()
                    now = time()
                    if timeout is not None and now - start_time >= timeout:
                        return False
                    rand_delay = random()
                    if timeout is not None:
                        if now + rand_delay - start_time >= timeout:
                            rand_delay = timeout - now - start_time
                        sleep(rand_delay)


    def unlock(self):
        try:
            os.remove(self.path)
        except OSError:
            pass

    def processIsAlive(self, pid):
        return LockFile.pid_exists(int(pid))
