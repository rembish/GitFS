#!/usr/bin/env python2
# SelectServer.py  -*- python -*-
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

class SelectMixIn:
    """ This mixin when applied to a socket servers, changes the model to use a single thread and dispatch
    requests to different handleers based on the results of calling select.  It keeps track of all the requests
    and calls one whenever there is room for reading or writting, as appropriate.
    """
