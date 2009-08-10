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
"""ircstats - a little script to parse XML IRC logs and gather stats from them

Cf. http://forge.blueoxen.net/wiki/IRC_Analytics
Cf. RFC 2812
Cf. http://colloquy.info/project/wiki/Development/Styles/LogFileFormat
"""

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
import xml.dom.minidom as md
from xml.dom import NotSupportedErr as NotSupportedError
import uuid
import os

import yaml

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
DEBUG     = False
VERSION   = "0.02x"
LOG_START = None
LOG_END   = None
MSGCOUNT  = 0
ACTCOUNT  = 0

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
class IRCUser(object):
    def __init__(self, nick, time):
        """nick is new to the log stream; create them and then join them."""
        self.id         = str(uuid.uuid4())
        self.nick       = nick
        self.nicks      = []
        self.join_times = []
        self.part_times = []
        self.messages   = {}           # XXX: no validation to prevent timestamp collisions
        self.references = {}           # XXX: no validation to prevent timestamp collisions
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
        pad = ' ' * len(self.nick)
        s  = self.nick + ": AKA " + str(self.AKAs)  + '\n'
        s += '\t' + 'joins' + ' ' + str([str(t) for t in self.join_times]) + '\n'
        s += '\t' + 'parts' + ' ' + str([str(t) for t in self.part_times]) + '\n'
        s += '\t' + 'said' + "  " + str(self.messages) + '\n'
        s += '\t' + 'refTo' + ' ' + str(self.references) + '\n'
        s += '\t' + 'acts' + "  " + str(self.actions) + '\n'
        return s

    def addNick(self, nickname):
        """Adds a nickname to the list for this user."""
        if nickname not in self.nicks:
           self.nicks.append(nickname)

class IRCNameMapper(object):
    """Maps IRC user names to UUIDs, Real names to UUIDs, and UUIDs to IRCUsers"""

    def __init__(self, mapping_yaml = 'usernames.yaml'):
        """Builds up the initial name mapping tables from YAML data on disk."""
        self.__yaml_data = {}
        self.__ircUserTable = {} # FIXME: in this vision, maps uuids -> user objects # should be a shelf # that may require copy, write, copy, write semantic
        self.__commonNames = {}  # FIXME: in this vision, maps names, nicks -> uuids

        self.__yaml_data = yaml.safe_load(open(f, 'r'))
        # FIXME: we should have IRC user dict loaded someplace, and it should 
        #        be our ircUserTable
        #
        #        For the case where we're *not* storing it, we should build it here.

        raise Exception, "Not Implemented"

    def __len__(self):
        """Return the number of unique user objects being tracked."""
        return len(self.__ircUserTable.keys())

    def __getitem__(self, key):
        if key in self.__ircUserTable
            return self__ircUserTable[key]
        elif key in self.__commonNames
            return self.__ircUserTable[ self.__commonNames[ key ] ]
        else:
            raise KeyError, "No such UUID or nick:" + str(key)

    def __setitem__(self, nick, user_object):
        """Maps a nickname to a particular user object"""
        id = user_object.id
        if id in self.__ircUserTable:
           self.__commonNames[nick] = user_object
           user_object.addNick(nick)

    def __iter__(self):
        for uuid in self.__ircUserTable.keys():
            yield uuid

    def __contains__(self, item):
        return (item in self.__ircUserTable) or (item in self.__commonNames)

    def merge(self, uuid1, uuid2):
        """Makes UUID1 and UUID2 refer to the same user object; returns new UUID"""
        raise Exception, "Not Implemented"

    def write_yaml(self, yaml = 'usernames.yaml'):
        """Write out a yaml file reflecting the current state of the user tables."""
        new_yaml_data = {}
        for key in self.__ircUserTable.keys():
            if key in self.__yaml_data:
                new_yaml_data[key] = self.__yaml_data[key]
            else:
                new_yaml_data[key] = self.yamlifyIRCUser(self.__ircUserTable[key])
        
        if os.access(yaml, os.F_OK) and os.access(yaml, os.W_OK):
            os.rename(yaml, yaml+'.bak')
        f = open(yaml, 'wb')
        yaml.dump(new_yaml_data, f, indent=4)

ircUserTable = {} 

#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
def getIRCUserForNick(irc_nick):
    """Checks whether we've ever seen this nick and returns the corresponding user"""

    # FIXME:
    # Here we should EXPECT:
       # The yaml data has been read in, and processed into uuid->name,nick and nick->uuid,name mappings
    # Here we should DO:
       # look up irc_nick in that table to get a UUID.  If there is not one, generate one
       # stick it back into the YAML dictionary of mappings
       # use a separate UUID->UserObject mapping to get the user object

    if irc_nick not in ircUserTable:
        ircUserTable[irc_nick] = IRCUser(irc_nick, LOG_START)
        if DEBUG: print irc_nick

    user_object = ircUserTable[irc_nick]

def handleLogDOM(dom):
    """Process the elements in a colloquy log DOM"""
    global LOG_START 
    LOG_START = dom.getAttribute('began')
    for child in dom.childNodes:
        if child.tagName == u"envelope":         # one or more lines from a user
            handleEnvelope(child)
        elif child.tagName == u"event":          # IRC server event
            handleEvent(child)
        else:                                    # violates log spec
            raise NotSupportedError, "Unknown child node " + child.tagName

    for user in ircUserTable.keys():
        ircUserTable[user].part(LOG_END)

def handleEnvelope(child):
    """Pick the relevant data off of a blob of messages from a single user."""

    global LOG_END
    global MSGCOUNT
    global ACTCOUNT

    irc_nick = getIrcNickAndValidate(child.getElementsByTagName('sender'))
    user_object = getIRCUserForNick(irc_nick) # FIXME: implement this

    for message in child.getElementsByTagName('message'):

        timestamp = message.getAttribute('received')
        pretty    = message.toprettyxml(encoding="utf-8")

        if message.getAttribute('type') == u"notice":
            handleMessageNotice(user_object, timestamp, pretty)
        elif message.getAttribute('action'):
            user_object.action(timestamp, pretty)
            ACTCOUNT += 1
        else:
            user_object.message(timestamp, pretty)
            MSGCOUNT += 1

        LOG_END = timestamp

def handleMessageNotice(user_object, timestamp, message):
    print "------------------------------------------------------------------------------"
    print "System notice detected, but currently unsupported by the parser."
    print "Now that there's some sample input for what notices look like,"
    print "this can be fixed."
    print
    print message
    print "------------------------------------------------------------------------------"

def handleEvent(child):
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

def count_messages(user):
    tally = 0
    if user == None:
        for user in ircUserTable.values():
            tally += count_messages(user)
    else: 
        return len(user.messages.keys())
    return tally

def count_actions(user):
    tally = 0
    if user == None:
        for user in ircUserTable.values():
            tally += count_actions(user)
    else: 
        return len(user.actions.keys())
    return tally
        
def usersByName():
    for name in sorted(ircUserTable.keys()):
        yield ircUserTable[name]

def statsForUser(user):
    """Returns (nick, message_count, act_count, message_ratio, act_ratio)"""

    nick = user.nick
    msgs = count_messages(user)
    acts = count_actions(user)
    msgrat = float(msgs)/MSGCOUNT
    actrat = float(acts)/ACTCOUNT

    return (nick, msgs, acts, msgrat, actrat)

def setup_optparse():
    import optparse
    usage = "usage: %prog [options] file1.xml [file2.xml] [...]"
    parser = optparse.OptionParser(usage=usage, version=VERSION)
    parser.add_option('-c', "--csv",      dest="csv",      action="store_true", default=False, 
                      help="Write a CSV-formatted file of all statistics to stdout")
    parser.add_option('-t', "--totals",   dest="totals",   action="store_true", default=False, 
                      help="Output summary totals of messages and actions")
    parser.add_option('-m', "--messages", dest="messages", action="store_true", default=False, 
                      help="Output message counts per username")
    parser.add_option('-a', "--actions",  dest="actions",  action="store_true", default=False, 
                      help="Output action counts per username")
    parser.add_option('-l', "--lurkers",  dest="lurkers",  action="store_true", default=False, 
                      help="Output list of lurkers - users who don't say anything")
    parser.add_option('-d', "--debug",    dest="debug",    action="store_true", default=False, 
                      help="Enable debug mode.  Really, it's not that great.")
    options, args = parser.parse_args()
    return parser


#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+#########+
if __name__ == "__main__":

    option_parser = setup_optparse()
    options, args = option_parser.parse_args()

    if (len(args) == 0): option_parser.error("At least one Colloquy XML-formatted IRC log file must be specified.")
    if options.debug: DEBUG = True

    # Read in user mapping file
    uuidToNames = setup_yaml('usernames.yaml')
    
    # Read in and process user log file
    for filename in args:
        dom = md.parse(filename)
        assert dom.documentElement.tagName == u"log"
        handleLogDOM(dom.documentElement)
        dom.unlink()

    if options.totals:
        print "Total messages:", MSGCOUNT + ACTCOUNT
        print "Messages:", MSGCOUNT
        print "Actions:", ACTCOUNT

    if options.messages:
        print "Messages by user:"
        print '\t%s  %s  %15s' % ("Msgs", "%Tot", "IRC Nick")
        for user in usersByName():
            msgs = count_messages(user)
            if msgs > 0:
                print '\t %3d  %.2f  %20s' % (msgs, float(msgs)/MSGCOUNT, user.nick)

    if options.actions:
        print "Actions by user:"
        print '\t%s  %s  %15s' % ("Acts", "%Tot", "IRC Nick")
        for user in usersByName():
            acts = count_actions(user)
            if acts > 0:
                print '\t %3d  %.2f  %20s' % (acts, float(acts)/ACTCOUNT, user.nick)

    if options.lurkers: 
        lurkers = []
        semilurk = []
        for user in usersByName():
            stats = statsForUser(user)
            if stats[1] == 0 and stats[2] == 0:
                lurkers.append(user.nick)
            elif stats[2] == 0:
                semilurk.append(user.nick)
        if len(lurkers) == 0:
            print "No Lurkers"
        else:
            print "Lurkers:"
            for name in lurkers:
                print '\t %s' % name
        if len(semilurk) == 0:
            print "No action-only users"
        else:
            print "Action-only users:"
            for name in semilurk:
                print '\t %s' % name

    if options.csv:
        import csv, sys
        csv.register_dialect("ooffice_like", delimiter=',', skipinitialspace=True, lineterminator="\n", quoting=csv.QUOTE_NONNUMERIC)
        def statsTuples():
            yield ("IRC Nick", "Message Count", "Action Count", "Messages/Total Messages", "Actions/Total Actions")
            for user in usersByName():
                yield statsForUser(user)
        csv.writer(sys.stdout, dialect="ooffice_like").writerows(statsTuples())
