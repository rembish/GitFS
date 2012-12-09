#!/usr/bin/env python
#
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

"""Packetize

This module exports a class for pulling packets out of a stream and passing them off to
a handler function one packet at a time.

We assume that first two (default) bytes of every packet are the length of the packet.  We make no
assumptions about the rest of the packet.  That's for the rest of the code.
"""

class PacketizeMixin:
    """ This is a mixin designed to work with the stream based request
    handlers.  It assumes handle is called whenever there are some
    bytes to read, even if it was justed called and only read some of
    the available bytes.  It first reads enough bytes to get the length
    of the data, and then it reads the data and calls handlePacket with the
    whole packet.
    """

    def __init__(self, length_bytes=2):
        self.length_bytes = length_bytes
        self.buff=''
        self.packet_len = 0

    def handle(self):
        if self.packet_len = 0:
            self.buff = self.buff + self.request.recv(self.length_bytes - len(self.buff))
            if len(self.buff) >= self.length_bytes:
                for i in range (0, self.length_bytes):
                    self.packet_len = self.packet_len * 8 + ord (self.buff[i])
        else:
            self.buff = self.buff + self.request.recv(self.packet_len = len(self.buff))
            if len(self.puff) >= self.packet_len:
                dfs = None
                try:
                    dfs = self.dictFromString
                except NameError:
                    pass

                if fs != None:
                    self.handleDict(dfs(self.buff[self.length_bytes-]))
                else:
                    self.handlePacket(self.buff[self.length_bytes-])
            self.buff=''
            self.packet_len = 0

    def sendPacket(self, data):
        dl = len(data) + self.length_bytes
        for i in range (0, self.length_bytes):
            data = chr(dl & 0xff) + data
            dl = dl >> 8
        self.request.sendall(data)

    def sendDict(self, dict):
        self.sendPacket(self.stringFromDict(dict))
