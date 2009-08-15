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
"""

from xml.dom import NotSupportedErr as NotSupportedError
from datetime import datetime

from UserStats import UserStats

def getUserStatsForNick(irc_nick, userTable, logStartTime):
    """Checks whether we've ever seen this nick and returns the corresponding user"""

    if irc_nick not in userTable:
        userTable[irc_nick] = UserStats(irc_nick, logStartTime, userTable.getID())

    return userTable[irc_nick]

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
            handleEvent(child, userTable)
        else:                                    # violates log spec
            raise NotSupportedError, "Unknown child node " + child.tagName

    for user in userTable.keys():
        userTable[user].part(logEndTime)

def handleEnvelope(child, userTable, logStartTime):
    """Pick the relevant data off of a blob of messages from a single user."""

    logEndTime = None
    irc_nick = getIrcNickAndValidate(child.getElementsByTagName('sender'))
    user_object = getUserStatsForNick(irc_nick, userTable, logStartTime) 

    for message in child.getElementsByTagName('message'):

        timestamp = message.getAttribute('received')
        timestamp = datetime.strptime(message.getAttribute('received')[:19], "%Y-%m-%d %H:%M:%S")
        pretty    = message.toprettyxml(encoding="utf-8")

        if message.getAttribute('type') == u"notice":
            handleMessageNotice(user_object, timestamp, pretty)
        elif message.getAttribute('action'):
            user_object.action(timestamp, pretty)
        else:
            user_object.message(timestamp, pretty)

        logEndTime = timestamp
    return logEndTime

def handleMessageNotice(user_object, timestamp, message):
    print "------------------------------------------------------------------------------"
    print "System notice detected, but currently unsupported by the parser."
    print "Now that there's some sample input for what notices look like,"
    print "this can be fixed."
    print
    print message
    print "------------------------------------------------------------------------------"

def handleEvent(child, userTable):
    print "------------------------------------------------------------------------------"
    print "Event detected, but currently unsupported by the parser."
    print "Now that there's some sample input for what events look like,"
    print "this can be fixed."
    print
    print "After event handling is implemented, re-run this script for more"
    print "accurate stats."
    print 
    print child
    print "------------------------------------------------------------------------------"

def getIrcNickAndValidate(element_list):
    first = element_list[0]
    if len(element_list) > 1:
        parent = first.parentNode
        raise NotSupportedError, "Multiple senders on node: " + parent.toprettyxml()
    id = first.getAttribute('identifier')
    if id == '':
        return first.firstChild.nodeValue
    else: 
        return id


