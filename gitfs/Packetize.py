#!/usr/bin/env python2
# Packetize.py  -*- python -*-
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

import logging
import errno

"""Packetize

This module exports a class for pulling packets out of a stream and passing them off to
a handler function one packet at a time.

We assume that first two (default) bytes of every packet are the length of the packet.  We make no
assumptions about the rest of the packet.  That's for the rest of the code.
"""

class PacketizeMixIn:
    """ This is a mixin designed to work with the stream based request
    handlers. It first reads enough bytes to get the length of the
    data, and then it reads the data and calls handlePacket with the
    whole packet.

    Uses member variables:_length_bytes, _packet_len and _buff
    """

    def getPacket(self):
        # XXXXX Fixme: there has to be a bette way to do this
        try:
            if self._length_bytes < 1:
                self._length_bytes = 2
        except AttributeError:
            self._length_bytes = 2
            
        try:
            self._packet_len
            self._buff
        except AttributeError:
            self._packet_len = 0
            self._buff=''
            
        try:
            while True:
                if self._packet_len == 0:
                    logging.debug('getting packet length length_bytes = %s, bytes_in_buff = %s' %(self._length_bytes, len(self._buff)))
                    red = self.request.recv(self._length_bytes - len(self._buff))
                    if len(red) == 0:
                        logging.debug("recv returned 0 length string.")
                        return False
                    self._buff = self._buff + red
                    if len(self._buff) >= self._length_bytes:
                        for i in range (0, self._length_bytes):
                            self._packet_len = self._packet_len * 8 + ord (self._buff[i])
                    logging.debug("packet_len = %s" %self._packet_len)
                else:
                    logging.debug("getting rest of packet")
                    red =self.request.recv(self._packet_len - len(self._buff))
                    if len(red) == 0:
                        logging.debug("recv returned 0 length string(2).")
                        #happens when the socket gets closed on us in the middle.
                        return False
                    self._buff = self._buff + red
                    logging.debug("buff now: %s" %self._buff)

                    if len(self._buff) >= self._packet_len:
                        logging.debug('buff_len = %s, packet_len = %s' %(len(self._buff), self._packet_len))
                        dfs = None
                        try:
                            dfs = self.dictFromString
                        except AttributeError:
                            pass

                        if dfs != None:
                            self.handleDict(dfs(self._buff[self._length_bytes:self._packet_len]))
                        else:
                            self.handlePacket(self._buff[self._length_bytes:self._packet_len])
                        self._buff=''
                        self._packet_len = 0
                        return True
                    
        except IOError as ioe:
            logging.debug ("ioerror: %s" %ioe)
            if ioe.errno != errno.EAGAIN and ioe.errno != errno.EWOULDBLOCK:
                raise ioe
        
    def handle(self):
        while self.getPacket():
            pass

    def sendPacket(self, data):
        dl = len(data) + self._length_bytes
        for i in range (0, self._length_bytes):
            data = chr(dl & 0xff) + data
            dl = dl >> 8
        logging.debug('Sending %s bytes' %(len(data)))
        self.request.sendall(data)

    def sendDict(self, dict):
        self.sendPacket(self.stringFromDict(dict))
