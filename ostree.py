#!/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2015  Daniel Vrátil <dvratil@redhat.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA
#

import subprocess
import os.path

from dateutil import parser
from stat import *

class Commit:
    def __init__(self, lines):
        self.rev = None
        self.date = None
        self.msg = None

        if len(lines) < 4:
            return

        self.rev = lines[0][7:]
        self.date = parser.parse(lines[1][7:])
        self.date = self.date.replace(tzinfo = None)
        self.msg = '\n'.join(lines[2:])

class Diff:
    Added = 1
    Modified = 2
    Removed = 3

    def __init__(self, line):
        self.mode = 0
        self.filePath = None

        line = line.strip()
        if line.startswith('A'):
            self.mode = Diff.Added
        elif line.startswith('M'):
            self.mode = Diff.Modified
        elif line.startswith('R'):
            self.mode = Diff.Removed

        self.filePath = line.rsplit(' ', 2)[1]

class FileEntry:
    File = 1
    Dir = 2
    Symlink = 3

    def __init__(self, line):
        line = line.strip()
        lcols = line.split(' ', 3)
        rcols = line.rsplit(' ', 2)

        if len(lcols) < 3:
            return

        if lcols[0][0] == '-':
            self.type = FileEntry.File
        elif lcols[0][0] == 'd':
            self.type = FileEntry.Dir
        elif lcols[0][0] == 'l':
            self.type = FileEntry.Symlink
        else:
            self.type = None

        mode = int(lcols[0][1:], 8)
        self.mode = ''
        self.mode += 'r' if mode & S_IRUSR == S_IRUSR else '-'
        self.mode += 'w' if mode & S_IWUSR == S_IWUSR else '-'
        self.mode += 'x' if mode & S_IXUSR == S_IXUSR else '-'
        self.mode += 'r' if mode & S_IRGRP == S_IRGRP else '-'
        self.mode += 'w' if mode & S_IWGRP == S_IWGRP else '-'
        self.mode += 'x' if mode & S_IXGRP == S_IXGRP else '-'
        self.mode += 'r' if mode & S_IROTH == S_IROTH else '-'
        self.mode += 'w' if mode & S_IWOTH == S_IWOTH else '-'
        self.mode += 'x' if mode & S_IXOTH == S_IXOTH else '-'

        self.uid = int(lcols[1])
        self.gid = int(lcols[2])
        self.size = int(rcols[1])
        self.filePath = rcols[2]
        self.fileName = os.path.basename(self.filePath)


class Repo:
    def __init__(self, repo):
        self._repo = repo

    def refs(self):
        return self._cmd(['refs']).split('\n')

    def revParse(self, rev):
        return self._cmd(['rev-parse', rev])

    def cat(self, rev, path):
        return self._cmd(['cat', rev, path], decode = False)

    def log(self, rev):
        log = self._cmd(['log', rev])
        rv = []
        commit = []
        for line in log.split('\n'):
            if line.startswith('commit '):
                rv.append(Commit(commit))
                commit = []
            else:
                commit.append(line)
        return rv

    def show(self, rev):
        commit = self._cmd(['show', rev])
        return Commit(commit.split('\n'))

    def diff(self, rev):
        diff = self._cmd(['diff', rev])
        rv = []
        for line in diff.split('\n'):
            rv.append(Diff(line))
        return rv

    def ls(self, rev, path, recursive = False):
        cmd = ['ls']
        if recursive:
            cmd += ['--recursive']
        cmd += [rev, path]
        ls = self._cmd(cmd)
        rv = []
        for line in ls.split('\n'):
            rv.append(FileEntry(rv))
        return rv


    def _cmd(self, args, decode = True):
        p = subprocess.Popen(['ostree'] + args + ['--repo=%s' % self._repo],
                             stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        out, _ = p.communicate()
        if decode:
            return out.decode('UTF-8').strip()
        else:
            return out
