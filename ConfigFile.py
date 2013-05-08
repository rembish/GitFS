#!/usr/bin/env python
# ConfigFile.py  -*- python -*-
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
import re
import logging

from ManyFile import ManyFile
from GFile import GFile

class ConfigFileException(Exception):
    def __init__(self, message, file, line):
        self.message = message
        self.file = file
        self.line = line

    def __str__(self):
        return '%s at %s(%d)' %(self.message, self.file, self.line)
    
class ConfigFile(object):
    def __init__(self):
        self.filename = None
        self.config={}
        self.docs={}
        self.comment = None

    def unescape(self, string):
        return string.decode()

    def addValue(self, current, key, value, cont):
        value = value.rstrip()
        value = self.unescape(value)
        if isinstance(current, dict):
            if cont:
                current[key] = current[key] + value
            else:
                current[key] = value
        elif isinstance(current, list):
            if key is not None and key != '':
                raise ConfigFileException('syntax error', f.filename(), f.filelineno())
            if cont:
                current.push(current.pop() + value)
            else:
                current.push(value)

    def stripComments(self, l):
        m = re.search(r'(\\\\)*#@\s*(?P<name>[a-zA-Z0-9_]*)\s*(?P<value>.*)', l)
        if m is not None:
            self.docs[m.gropu('name')] = self.docs[m.group('name')] + " " + m.group('value')
        m = re.search(r'(\\\\)*#', l)
        if m is not None:
            l = l[:m.end()- 1]
        return l

    def writeDict(self, f, d):
        for k,v in d.items():
            f.write(k + ': ');
            if isinstance(v, dict):
                f.write ('{')
                self.writeDict(f, v)
                f.write ('}')
            elif isinstance(v, list):
                f.write ('[')
                self.writeList(f, list)
                f.write(']')
            else:
                f.write(v)
            f.writeln(',')

    def writeList(self, f, l):
        for v in l:
            if isinstance(v, dict):
                f.write ('{')
                self.writeDict(f, v)
                f.write ('}')
            elif isinstance(v, list):
                f.write ('[')
                self.writeList(f, list)
                f.write(']')
            else:
                f.write(v)
            f.writeln(', ')
                
        
    def writeFile(self, filename):
        f = GFile.open(filename, 'w')
        for n in ( 'title', 'mode', 'author', 'version' ):
            if n in self.docs:
                f.write ('#@%s %s\n' %(n, self.docs[n]))

        if self.comment is not None:
            for l in textwrap.wrap(self.comment):
                f.write('#@comment ' + l + '\n')

        self.writeDict(f, self.config)
        f.close()

    def setConfig(self, cf):
        self.config = cf

    def getConfig(self):
        return self.config

    def readFile(self, filenames):
        f = ManyFile(filenames)
        object_stack = []
        cont = False
        current = self.config
        key = ''
        for l in f:
            l = self.stripComments(l)
            while l is not None and len(l) > 0:
                l = l.lstrip()
                if len(l) == 0:
                    break
                if not cont:
                    if l[0] == '{':
                        l = l[1:]
                        object_stack.push({'Object' : current, 'Key': key})
                        obj = {}
                        if isinstance(current, dict):
                            current[key]=obj
                            current=current[key]
                            key=''
                        elif isinstance(current, list):
                            current.push(obj)
                            key = ''
                            current = obj
                        else:
                            raise ConfigFileException('Syntax Error', f.filename(), f.filelineno())
                        continue

                    if l[0] == '[':
                        l = l[1:]
                        obj = []
                        object_stack.push({'Object' : current, 'Key': key})
                        if isinstance(current, dict):
                            current[key]=obj
                            current=current[key]
                            key=''
                        elif isinstance(current, list):
                            current.push(obj)
                            key = ''
                            current = obj
                        else:
                            raise ConfigFileException('Syntax Error', f.filename(), f.filelineno())
                        continue
                    
                if l[0] == '}':
                    l = l[1:]
                    if not isinstance(current, dict):
                        raise ConfigFileException('unexpected } ', f.filename(), f.filelineno())
                    old = object_stack.pop()
                    current = old.object()
                    if current is None:
                        raise ConfigFileException('unexpected } ', f.filename(), f.filelineno())
                    key=''
                    continue
                if l[0] == ']':
                    l = l[1:]
                    if not isinstance(current, list):
                        raise ConfigFileException('unexpected ] ', f.filename(), f.filelineno())
                    old = object_stack.pop()
                    current = old.object()
                    if current is None:
                        raise ConfigFileException('unexpected } ', f.filename(), f.filelineno())
                    key=''
                    continue

                if l[0] == '$': 
                    # special case, it's a directive like $include, not a regular statement.
                    w = l[1:].split(maxsplit=1)
                    d=w[0]
                    a = None
                    if len(w) > 1:
                        a=w[1]
                    if d == 'include':
                        f.include(a)
                        break
                    raise ConfigFileException('unknown directive', f.filename(), f.filelineno())

                if l[0] == ',':
                    l=l[1:]
                    continue

                if isinstance(current, dict) and key == '' :
                    m = re.match(r'^(([^:=]|(\\\\)*\\[:=])+)\s*[:=]', l)
                    if m is not None:
                        key = m.group(1)
                        key.rstrip()
                        key = self.unescape(key)
                        l = l[m.end(0)+1:]
                        continue
                    else:
                        raise ConfigFileException('key: or key= expected', f.filename(), f.filelineno())

                if isinstance(current, dict):
                    closing = '}'
                else:
                    closing = ']'
                
                m = re.match(r'(([^,\%s]|(\\\\)*\\[,\%s])*)(?P<end>[,\%s])' %(closing, closing, closing),  l)
                if m is not None:
                    #logging.debug('found match key=%s value=%s' %(key, m.group(1)))
                    self.addValue(current, key, m.group(1), cont)
                    cont = False
                    key = ''
                    l = l[m.end(0)+1:]
                    if m.group('end') != ',':
                        l = closing + l
                    continue
                else:
                    #logging.debug('didn\'t find match using whole string key=%s value=%s' %(key, l))
                    self.addValue(current, key, l, cont)
                    cont = True
                    break

