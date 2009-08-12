#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
# Copyright (C) 2009  Joe Blaylock <jrbl@jrbl.org>
#
#This program is free software: you can redistribute it and/or modify it under 
#the terms of the GNU General Public License as published by the Free Software 
#Foundation, either version 3 of the License, or (at your option) any later 
#version.
#
#This program is distributed in the hope that it will be useful, but WITHOUT 
#ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
#FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more 
#details.
#
#You should have received a copy of the GNU General Public License along with 
#this program.  If not, see <http://www.gnu.org/licenses/>.
"""An object collecting data about a particular entity all in one place.

Currently set up for tracking IRC utterances and actions.
"""


# Classes
class UserStats(object):
    """Models all the interesting stats pertaining to a particular entity on IRC"""

    def __init__(self, nick, time, uid = None):
        """nick is new to the log stream; create them and then join them."""
        if uid == None:
            import uuid
            self.id         = str(uuid.uuid4())
        else:
            self.id     = uid
        self.nick       = nick
        self.nicks      = [nick]
        self.join_times = []
        self.part_times = []
        self.messages   = {}           # XXX: no validation to prevent timestamp collisions
        self.actions    = {}           # XXX: no validation to prevent timestamp collisions
        self.state      = 'new'        # new, joined, parted
        self.join(time)

    def join(self, time):
        if time not in self.join_times:
            self.join_times.append(time)
        self.state = 'joined'

    def part(self, time):
        """This user has left the channel"""
        if time not in self.part_times:
            self.part_times.append(time)
        self.state = 'parted'

    def message(self, time, text):
        """This user has said something.
        FIXME: the XML format tracks who we refer to; we should track that.
        FIXME: we can also extract who refers to us and track that.
        """
        self.messages[time] = text   

    def action(self, time, text):
        """User performed an action"""
        self.actions[time] = text

    def __str__(self):
        s  = self.nick + ": AKA " + str(self.nicks)  + '\n'
        s += '\t' + 'joins' + ' ' + str([str(t) for t in self.join_times]) + '\n'
        s += '\t' + 'parts' + ' ' + str([str(t) for t in self.part_times]) + '\n'
        s += '\t' + 'said' + "  " + str(self.messages) + '\n'
        s += '\t' + 'acts' + "  " + str(self.actions) + '\n'
        return s

    def addNick(self, nickname):
        """Adds a nickname to the list for this user."""
        if nickname not in self.nicks:
            self.nicks.append(nickname)


# Utility Functions


# Test Harness
if __name__ == "__main__":
    pass

