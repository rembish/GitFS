#!/usr/bin/env python2
# Queue.py  -*- python -*-
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

import logging
import sys
import tempfile
import os
import random

from threading import Thread, Lock, Condition


class Queue(object):
    def __init__(self, directory, method):
        self.method = method
        self.directory = tempfile.mkdtemp(directory)
        self.dir = os.path.realpath(os.path.abspath(directory))
        self.queue = []
        self.in_process = []
        self.map = {}
        self.lock = Lock()
        self.more = Condition()
        self.less = Condition()

    def cleanup(self):
        shutil.rmtree(self.dir)
        
    def qsize(self):
        with self.lock:
            return len(self.queue)

    def empty(self):
        with self.lock:
            return len(self.queue) == 0

    def full(self):
        return False

    def put(self, item, block=True, timeout=None):
        with item.lock:
            if self.lock.acquire(block):
                try:
                    self.queue.append(item)
                    self.map[item.id()] = item
                finally:
                    self.lock.release()
                path = item.path(self.directory)
                item.write(path)
                with self.more:
                    self.more.notify()
            else:
                return False

    def put_nowait(self, item):
        return self.put(item, block=False)

    def get(self, block=True, timeout=None):
        logging.debug("queue.get block=%s" %block)
        item = None
        while item is None:
            with self.more:
                if self.lock.acquire(block):
                    try:
                        logging.debug("lock aquired block=%s" %block)
                        if len(self.queue) > 0:
                            logging.debug("found one.")
                            item = self.method(self)
                            logging.debug("found item %s" %item)
                            del self.map[item.id()]
                            self.in_process.append(item)
                    finally:
                        logging.debug("releasing lock.")
                        self.lock.release()
                if item is not None:
                    return item
                if not block:
                    logging.debug("item is None and non-blocking.")
                    return None
                logging.debug("waiting for more items, block=%s item=%s.\n" %(block, item))
                self.more.wait()
        
        with item.lock:
            path = item.path(self.directory)
            item.refresh(path)
            item.remove(path)
            return item

    
    def get_nowait(self):
        return self.get(block=False)

    def task_done(self, item):
        with item.lock:
            with self.lock:
                self.in_process.remove(item)
                with self.less:
                    self.less.notifyAll()
            
    def join(self):
        with self.less:
            while len(self.in_process) > 0 or len(self.queue) > 0:
                self.less.wait()

class ItemBase:
    """a do nothing item base for testing, or to derive real items from.
    """
    def __init__(self):
        self.ident = random.random()
        self.lock = Lock()

    def id(self):
        return self.ident

    def lock(self):
        return self.lock.acquire()

    def unlock(self):
        return self.lock.release()

    def write(self, path):
        return False

    def refresh(self, path):
        return False

    def remove(self, path):
        return False

    def path(self, dir):
        return dir

def joinTest(q):
    q.join()
    if not q.empty():
        raise Exception("queue not empty")

def putTest(q):
    for i in range(100):
        q.put(ItemBase())

def getTest(q):
    i = q.get_nowait()
    while i is not None:
        q.task_done(i)
        i = q.get_nowait()
        
def main():
    q = Queue(directory='/', method=lambda s: s.queue.pop() )
    q.put(ItemBase())
    jt = Thread(target=joinTest, args=(q,) )
    jt.start()
    pt = []
    logging.debug ("Starting put threads.")
    for i in range(10):
        t = Thread(target=putTest, args=(q,))
        t.start()
        pt.append(t)

    logging.debug ("joining put threads.")
    for t in pt:
        t.join()

    pt = []
    gt = []

    logging.debug ("Starting put/get threads.")
    for i in range(10):
        t = Thread(target=putTest, args=(q,))
        t.start()
        pt.append(t)

        t = Thread(target=getTest, args=(q,))
        t.start()
        gt.append(t)

    logging.debug ("Joining put threads.")
    for t in pt:
        t.join()

    logging.debug ("Joining get threads.")
    for t in gt:
        t.join()

    logging.debug ("Calling get one last time.")
    getTest(q)
    logging.debug ("Joining join thread.")
    jt.join()
    
if __name__ == "__main__":
    logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
    main ()


    
