#!/usr/bin/env python2
# HostInfo.py  -*- python -*-
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
"""HostInfo this module exports the HostInfo class that is used to contain
information about a host and match it up to other information.
"""

import socket


class HostInfo(object):
    def __init__(self):
        self.ipAddress = None
        self.hostname = None

    def update(self):
        self.hostname = socket.gethostname()
        self.ipAddress = []
        try:
            ainfo = socket.getaddrinfo(self.hostname, None)
            self.ipAddress = ainfo
        except socket.gaierror:
            pass

    def matchAddress(self, ip):
        # addresses are in net order.
        bestmatch = 0
        count=0
        for ainfo in self.ipAddress:
            count = 0
            ip_address = ainfo[4]
            if len(ip) != len(ip_address):
                break

            for i in range(0, len(ip)):
                a1 = ord (ip[i])
                a2 = ord (self.ipAddress[i])
                a3 = a1 & a2
                for j in range (0, 8):
                    if a3 & 0x80 == 0:
                        break
                    count = count + 1
                    a3 = a3 << 1
            if count > bestmatch:
                bestmatch = count
                
        return bestmatch

    def matchHostName(self, key):
        me = self.hostname.split('.')
        thee = key.split('.')
        score = 0
        point = 1
        while len(thee) > 0 and len(me) > 0:
            w1 = me.pop()
            w2 = thee.pop()
            if w1 != w2:
                return score
            score = score + point
            if point == 7:
                point = 8
                
            if point == 1:
                point = 7

        return score
