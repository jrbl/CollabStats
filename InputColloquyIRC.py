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
"""XML parser for Collquy XML-formatted IRC transcripts.

Currently just a pile of functions.  Safe for "from InputColloquyIRC import *".

Cf. http://forge.blueoxen.net/wiki/IRC_Analytics
Cf. RFC 2812
Cf. http://colloquy.info/project/wiki/Development/Styles/LogFileFormat
"""

from xml.dom import NotSupportedErr as NotSupportedError
from datetime import datetime

from UserStats import UserStats

class PlainTextIRCParser(object):

    def __init__(self, logfile_object, user_table):
        self.log = logfile_object
        self.user_table = user_table
        self.res = {
            'time': re.compile("^\(\[\d{4}-\d{2}-\d{2} \d{2}::\d{2}:\d{2}]\)"),               #[2009-07-21 12::33:42]
            'nick': re.compile("] \([a-zA-Z\[\]_\\`^{}|][0-9a-zA-Z\[\]_\\`^{}|\-]*\): "),     #] nickname: text
        }
        self.fils = {
            'time': [self._regex2datetime, "[%Y-%m%-%d %H::%M:%S]"],
            'nick': [self._getIRCnick, ],
        }
        self.start_time = None
        self.end_time = None

    def _regex2datetime(self, match_obj, timestrl):
        return datetime.strptime(match_obj.group(), timestrl[0])

    def _getIRCnick(self, match_obj, empty = None):
        return self._ircLower(match_obj.group)

    def _ircLower(self, s):
        """Convert the input string to all-lower-case, with attempts to respect RFC 2812 s2.2"""
        s = s.lower()
        s.replace('[', '{')
        s.replace(']', '}')
        s.replace('\\', '|')
        s.replace('~', '^')
        return s

    def _match_and_apply(self, key, str):
        regex = self.res[key]
        m = regex.match(str)
        if m != None:
            return self._apply_filter(key, m)

    def _apply_filter(self, key, match_object):
        func = self.fils[key][0]
        args = self.fils[key][1:]
        return func(match_object, args)

    def process(self, userTable):
        first = self.log.readline()
        self.start_time = self._match_and_apply('time', first)
        dispatch_to_handler(first)
        for line in self.log.readlines():
            self.end_time = self.dispatch_to_handler(line)
        for user in userTable.keys():
            userTable[user].part(self.end_time)

    def dispatch_to_handler(self, line):
        """Given a line of text, figures out what handler to use on it"""
        dt   = self._match_and_apply('time', line)
        nick = self._match_and_apply('nick', line)
        if nick == None:
           # server msg, action or event
           raise Exception, "Not implemented.  FIXME XXX HACK" # FIXME XXX HACK
        else:
            end = self.handle_message(dt, nick, line)
        return end

    def handle_message(date, nick, line):
        """Book an irc message to a particular user nick"""
        raise Exception, "Not implemented" # FIXME XXX HACK
        user_object = None
        text_offset = nick.span()[1]+1
        msg = line[text_offset:]
        user_object.message(date, msg)

def handleEnvelope(child, userTable, logStartTime):
    """Pick the relevant data off of a blob of messages from a single user."""

    logEndTime = None
    irc_nick = getIrcNickAndValidate(child.getElementsByTagName('sender'))
    user_object = getUserStatsForNick(irc_nick, userTable, logStartTime) 

    for message in child.getElementsByTagName('message'):

        timestamp = message.getAttribute('received')
        timestamp = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
        pretty    = message.toprettyxml(encoding="utf-8")

        if message.getAttribute('type') == u"notice":
            handleMessageNotice(user_object, timestamp, pretty)
        elif message.getAttribute('action'):
            user_object.action(timestamp, pretty)
        else:
            user_object.message(timestamp, pretty)

        logEndTime = timestamp
    return logEndTime

def handleLogDOM(dom, userTable):
    """Process the elements in a colloquy log DOM"""
    logStartTime = datetime.strptime(dom.getAttribute('began')[:19], "%Y-%m-%d %H:%M:%S")
    logEndTime = None
    for child in dom.childNodes:
        if child.nodeName == u"envelope":         # one or more lines from a user
            logEndTime = handleEnvelope(child, userTable, logStartTime)
        elif child.nodeName == "#text":
            for c in child.data:
                if c not in '\t\n\x0b\x0c\r ':
                    print "Unexpected text node: \"" + str(child.data) + "\""
                    print "continuing..."
        elif child.nodeName == u"event":          # IRC server event
            logEndTime = handleEvent(child, userTable, logStartTime)
        else:                                    # violates log spec
            raise NotSupportedError, "Unknown child node " + child.tagName

    for user in userTable.keys():
        userTable[user].part(logEndTime)

def ircLower(s):
    """Convert the input string to all-lower-case, with attempts to respect RFC 2812 s2.2"""
    s = s.lower()
    s.replace('[', '{')
    s.replace(']', '}')
    s.replace('\\', '|')
    s.replace('~', '^')
    return s

def getUserStatsForNick(irc_nick, userTable, logStartTime):
    """Checks whether we've ever seen this nick and returns the corresponding user"""

    if irc_nick not in userTable:
        userTable[irc_nick] = UserStats(irc_nick, logStartTime, userTable.getID())

    return userTable[irc_nick]

def handleMessageNotice(user_object, timestamp, message):
    print "------------------------------------------------------------------------------"
    print "System notice detected, but currently unsupported by the parser."
    print "Now that there's some sample input for what notices look like,"
    print "this can be fixed."
    print
    print message
    print "------------------------------------------------------------------------------"

def handleEvent(child, userTable, logStartTime):
    logEndTime = None
    timestamp = child.getAttribute('occurred')
    event_name = child.getAttribute('name')
    timestamp = datetime.strptime(timestamp[:19], "%Y-%m-%d %H:%M:%S")
    whos = child.getElementsByTagName('who')
    if len(whos) > 0:
        irc_nick = getIrcNickAndValidate(whos)
    else:
        pass # this is odd, and doesn't it violate the Colloquy spec?  yeeagh
        # XXX: ignore it until it becomes a problem

    if event_name == "memberParted":
        user_object = getUserStatsForNick(irc_nick, userTable, logStartTime)
        user_object.part(timestamp)
    elif event_name == "memberJoined":
        user_object = getUserStatsForNick(irc_nick, userTable, logStartTime)
        user_object.join(timestamp)
    elif event_name == "memberNewNickname":
        new = irc_nick
        old = getIrcNickAndValidate(child.getElementsByTagName('old'))
        user_object = getUserStatsForNick(old, userTable, logStartTime)
        user_object.addNick(new)
    elif event_name == "newNickname":
        pass
    else:
        print "Unhandled event "+event_name

    logEndTime = timestamp
    return logEndTime

def getIrcNickAndValidate(element_list):
    try:
        first = element_list[0]
    except IndexError, msg:
        print element_list
        raise
    if len(element_list) > 1:
        parent = first.parentNode
        raise NotSupportedError, "Multiple senders on node: " + parent.toprettyxml()
    id = first.getAttribute('identifier')
    if id == '':
        return ircLower(first.firstChild.nodeValue)
    else: 
        return ircLower(id)


