#!/usr/bin/env python
# -*- coding: utf-8 -*-
#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
#Copyright (C) 2009  Joe Blaylock <jrbl@jrbl.org>
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
#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
"""ircstats - a little script to parse irc logs and gather stats from them

Cf. http://forge.blueoxen.net/wiki/IRC_Analytics
Cf. RFC 2812
"""

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
import optparse
import re
import datetime

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
DEBUG   = True
VERSION = "0.01"
DATE_FORMAT = "[YYYY-MM-DD HH::mm:ss]"
DATE_LENGTH = len(DATE_FORMAT)
IrcUserTable = {}

date_chars = '\[(?P<year>[12][09][0-9][0-9])-(?P<month>[01][0-9])-(?P<day>[0-3][0-9]) (?P<hour>[0-2][0-9])::(?P<minute>[0-5][0-9]):(?P<second>[0-5][0-9])]'
nick_chars = '[a-zA-Z\[\]_\\`^{}|][0-9a-zA-Z\[\]_\\`^{}|\-]*'
colloquy_part_chars = '» (?P<nick>' + nick_chars + ') left the chat room.'
colloquy_join_chars = '» (?P<nick>' + nick_chars + ') joined the chat room.'
colloquy_name_chars = '» (?P<nick1>' + nick_chars + ') is now known as (?P<nick2>' + nick_chars + ').'

date_re = re.compile(date_chars)
nick_re = re.compile(nick_chars)
c_part_re = re.compile(colloquy_part_chars)
c_join_re = re.compile(colloquy_join_chars)
c_name_re = re.compile(colloquy_name_chars)

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
class IrcUser(object):
    def __init__(self, nick, time):
        """nick is new to the log stream; create them and then join them."""
        self.nick       = nick
        self.join_times = []
        self.part_times = []
        self.utterances = {}           # XXX: no validation to prevent timestamp collisions
        self.references = {}           # XXX: no validation to prevent timestamp collisions
        self.actions    = {}           # XXX: no validation to prevent timestamp collisions
        self.AKAs       = []

        self.join_times.append(time)

    def join(self, time):
        """This user has joined the channel"""
        if time not in self.join_times:
           self.join_times.append(time)

    def part(self, time):
        """This user has left the channel"""
        self.part_times.append(time)

    def utterance(self, time, text):
        """This user has said something"""
        self.utterances[time] = text   

    def referrant(self, time, referrer, text):
        """Somebody talked about (or to) this user"""
        self.references[time] = (referrer, text)

    def action(self, time, text):
        """User performed an action"""
        self.actions[time] = text

    def nickChange(self, newnick):
        """User changed nicks
        
        FIXME: we can rely on conventions like foo->fooaway or foo->foo|food to strongly imply which nick is 
               canonical; we should try to do that parsing.
        """
        if newnick not in self.AKAs:
           self.AKAs.append(newnick)

    def __str__(self):
        pad = ' ' * len(self.nick)
        s  = self.nick + ": AKA " + str(self.AKAs)  + '\n'
        s += '\t' + 'joins' + ' ' + str([str(t) for t in self.join_times]) + '\n'
        s += '\t' + 'parts' + ' ' + str([str(t) for t in self.part_times]) + '\n'
        s += '\t' + 'said' + "  " + str(self.utterances) + '\n'
        s += '\t' + 'refTo' + ' ' + str(self.references) + '\n'
        s += '\t' + 'acts' + "  " + str(self.actions) + '\n'
        return s

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
def ircLower(s):
    """Convert the input string to all-lower-case, with attempts to respect RFC 2812 s2.2"""
    s = s.lower()
    s.replace('[', '{')
    s.replace(']', '}')
    s.replace('\\', '|')
    s.replace('~', '^')
    return s

def process(file):
    """Process an IRC log file, line by line.  Assumes DATE_FORMAT timestamps and » on server actions."""

    startoff   = DATE_LENGTH
    first_time = None                                 # used to seed join times before start of logging
    last_time  = datetime.datetime(1900, 1, 1)        # used to seed part times after end of logging

    for line in file:
        line = line.strip()
        date_match = date_re.match(line)
        if date_match == None: continue
        text_part = line[startoff:]
        nick_match = nick_re.search(text_part)
        text_after_nick = text_part[nick_match.end():]

        date = apply(datetime.datetime, [int(x) for x in date_match.groups()])
        if not first_time:
            first_time = date
        if date > last_time:
            last_time = date

        nick_raw = nick_match.group()
        nick = ircLower(nick_raw)

        user_object = None
        try:
            user_object = IrcUserTable[nick]
        except KeyError:
            user_object = IrcUser(nick, date)
            IrcUserTable[nick] = user_object

        if (nick_match.start() > 1):   # Server msg. XXX: relies on client to insert noise like '»'
            action_match = c_join_re.search(line)          # JOIN
            if action_match != None:
                user_object.join(date)
            action_match = c_part_re.search(line)          # PART
            if action_match != None:
                user_object.part(date)
            action_match = c_name_re.search(line)          # NAME CHANGE
            if action_match != None:
                newnick = ircLower(action_match.groupdict()['nick2'])
                user_object.nickChange(newnick)
                IrcUserTable[newnick] = user_object        # FIXME: malicious users can clobber each others' state
        else:                          # Regular utterances and actions
             if (text_after_nick[0] == ':'):
                 user_object.utterance(date, text_after_nick[2:])
             else:
                 user_object.action(date, text_part)
    
    for user in IrcUserTable.values():
        if len(user.join_times) - len(user.part_times) == 1:
            user.part_times.append(last_time)

def count_utterances(user = None):
    tally = 0
    if user == None:
        for user in IrcUserTable.values():
            tally += count_utterances(user)
    else: 
        return len(user.utterances.keys())
    return tally

        
#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
if __name__ == "__main__":

    parser = optparse.OptionParser(version=VERSION)
    #parser.add_option('-r', "--trim-row", action="store", type="int", dest="r", metavar="ROW", help="trims row number ROW")
    #parser.add_option('-c', "--trim-col", action="store", type="int", dest="c", metavar="COL", help="trims column number COL")
    #parser.add_option('', "--ceq", action="store", nargs=2, dest="ceq_tup", metavar="COL VAL", help="trims column COL if its value is VAL")
    #parser.add_option('', "--clt", action="store", nargs=2, dest="clt_tup", metavar="COL VAL", help="trims row if column COL has value less than VAL.  ORs with --ceq.")
    #parser.add_option('', "--cgt", action="store", nargs=2, dest="cgt_tup", metavar="COL VAL", help="trims row if column COL has value greater than VAL.  ORs with --ceq.")
    options, args = parser.parse_args()

    for filename in args:
        f = open(filename)
        process(f)

    for name in sorted(IrcUserTable.keys()):
        print IrcUserTable[name]
