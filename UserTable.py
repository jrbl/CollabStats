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
"""Implements a system for mapping common names to UUIDs and UUIDs to UserObjs.

UserObjs can be any Python object with the following publicly accessible 
attributes and methods:
Attributes:
 id: a string representing a uuid.uuid4() 
 nicks: a list of the common names for UserObj that it knows about
 addNick(nick): a method adding an alternate common name to UserObj.nicks
 
Also takes pains to cache data between uses, caching the UUIDs and names 
in a user-editable YAML file, and the UserObjs into a cPickle.

YAML file format:
  uuid-string:
   'real name': some text
   'email': [ list, of, addresses ]
   'irc': [ list, of nicks ]
   'wiki': [list, of, userids ]
"""

import os

import DictDB
from IRCUser import IRCUser

import yaml


class UserTable(object):
    """Maps common names to UUIDs and UUIDs to user objects"""

    def __init__(self, mapping_yaml = 'usernames.yaml', ircUsersDB = 'contact_stats.pickle'):
        """Builds up the initial name mapping tables from YAML data on disk."""
        self.__ircUserTable = {}                 # maps uuids -> user objects 
        self.__commonNames = {}                  # maps nicks -> uuids
        self.__yaml_data = {}                    # maps uuids -> common names, other info

        self.__ircUserTable = DictDB.dbopen(ircUsersDB, flag='c', format='pickle')
        self.__yaml_data = yaml.safe_load( open( mapping_yaml, 'r' ))

        # Ensure all the tables maintain synchrony on data read
        for id in self.__ircUserTable.keys():
            for nick in self.__ircUserTable[id].nicks:
                self.__commonNames[nick] = id
        for id in self.__yaml_data.keys():
            real_name = self.__yaml_data[id]['real name']
            nicks = self.__yaml_data[id]['irc']
            if real_name != '':
                self.__commonNames[real_name] = id
            for nick in nicks:
                self.__commonNames[nick] = id
            if id not in self.__ircUserTable:
                user_object = IRCUser( nicks[0], -1 ) # XXX: should timestamp properly
                for nick in nicks: 
                    user_object.addNick(nick)
                self.__ircUserTable[id] = user_object

    def __getitem__(self, key):
        if key in self.__ircUserTable:
            return self.__ircUserTable[key]
        elif key in self.__commonNames:
            return self.__ircUserTable[ self.__commonNames[ key ] ]
        else:
            raise KeyError, "No such UUID or nick: '" + str(key) + "'"

    def __setitem__(self, nick, user_object):
        """Maps a nickname to a particular user object"""
        id = user_object.id
        if id in self.__ircUserTable:
            self.__commonNames[nick] = id
            user_object.addNick(nick)
        else:
            self.__ircUserTable[id] = user_object
            self.__commonNames[nick] = id

    def __iter__(self):
        ## FIXME: probably should iterate over user objects rather than id's ? 
        #         requires more changes to ircstats too
        for uuid in self.__ircUserTable.keys():
            yield uuid

    def __contains__(self, key):
        return (key in self.__ircUserTable) or (key in self.__commonNames)

    def merge(self, uuid1, uuid2):
        """Makes UUID1 and UUID2 refer to the same user object; returns new UUID"""
        # FIXME: Not implemented.  Important.
        raise Exception, "Not Implemented"

    def write_yaml(self, yaml_file = 'usernames.yaml'):
        """Write out a yaml file reflecting the current state of the user tables."""
        new_yaml_data = {}
        for key in self.__ircUserTable.keys():
            if key in self.__yaml_data:
                new_yaml_data[key] = self.__yaml_data[key]
            else:
                new_yaml_data[key] = self.yamlifyIRCUser(self.__ircUserTable[key])
        
        if os.access(yaml_file, os.F_OK) and os.access(yaml_file, os.W_OK):
            os.rename(yaml_file, yaml_file+'.bak')
        f = open(yaml_file, 'wb')
        yaml.dump(new_yaml_data, f, indent=4)

    def close(self):
        """Write out our data files"""
        self.write_yaml()
        self.__ircUserTable.sync()

    def yamlifyIRCUser(self, user_object):
        """Return a data structure conforming to our YAML format for user_object"""
        return { 'real name': '', 'email': [ '' ], 'irc': [str(nick) for nick in user_object.nicks], 'wiki': [ '' ] } 

    def keys(self):
        """Return a list of every UUID we're tracking - lazily"""
        for key in self.__ircUserTable.keys():
            yield key

    def __len__(self):
        """Return the number of unique user objects being tracked."""
        return len(self.__ircUserTable.keys())

    def idToName(self, id):
        """If id is in our database, give a real name if we have one, or else nicks[0]"""
        if id in self.__yaml_data:
            record = self.__yaml_data[id]
            name = record['real name']
            if name != '': return name
            else: return record['irc'][0]
            

