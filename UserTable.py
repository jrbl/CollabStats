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
 id: a string uniquely identify a user object's ID
 nicks: a list of the common names for UserObj that it knows about
 addNick(nick): a method adding an alternate common name to UserObj.nicks
 
Also takes pains to cache data between uses, caching the UUIDs and names 
in a user-editable YAML file, and the UserObjs into a cPickle.

YAML file format:
  uid-string:
   'real name': some text
   'email': [ list, of, addresses ]
   'irc': [ list, of nicks ]
   'wiki': [list, of, userids ]
"""

import os

import DictDB
from UserStats import UserStats

import yaml


class UserTable(object):
    """Maps common names to UUIDs and UUIDs to user objects"""

    def __init__(self, mapping_yaml = 'usernames.yaml', user_objects_db = 'contact_stats.pickle'):
        """Builds up the initial name mapping tables from YAML data on disk."""
        self.__userObjectTable = {}              # maps ids -> user objects 
        self.__commonNames = {}                  # maps nicks -> ids
        self.__yaml_data = {}                    # maps ids -> common names, other info
        self.last_id = 0

        self.__userObjectTable = DictDB.dbopen(user_objects_db, flag='c', format='pickle')
        self.__yaml_data = yaml.safe_load( open( mapping_yaml, 'r' ))

        # Set last_id higher than anything we've seen (necessary with sequential uids, not uuids)
        # XXX: oh my gods, this is crazy.  But at least it's user-editable, I guess?
        user_keys = sorted( self.__userObjectTable.keys() ) or [ 1 ]
        yaml_keys = sorted( self.__yaml_data.keys()       )       or [ 1 ]
        self.last_id = max(user_keys[ len(user_keys)-1 ], 
                           yaml_keys[ len(yaml_keys)-1 ])

        # Ensure all the tables maintain synchrony on data read
        for id in self.__userObjectTable.keys():
            for nick in self.__userObjectTable[id].nicks:
                self.__commonNames[nick] = id
        for id in self.__yaml_data.keys():
            real_name = self.__yaml_data[id]['real name']
            nicks = self.__yaml_data[id]['irc']
            if real_name != '':
                self.__commonNames[real_name] = id
            for nick in nicks:
                self.__commonNames[nick] = id
            if id not in self.__userObjectTable:
                user_object = UserStats( nicks[0], -1, id ) # XXX: should timestamp properly
                for nick in nicks: 
                    user_object.addNick(nick)
                self.__userObjectTable[id] = user_object

    def getID(self):
        """Gets the next number in the ID sequence.  NOT THREAD SAFE"""
        self.last_id += 1
        return self.last_id

    def __getitem__(self, key):
        if key in self.__userObjectTable:
            return self.__userObjectTable[key]
        elif key in self.__commonNames:
            return self.__userObjectTable[ self.__commonNames[ key ] ]
        else:
            raise KeyError, "No such UUID or nick: '" + str(key) + "'"

    def __setitem__(self, nick, user_object):
        """Maps a nickname to a particular user object"""
        id = user_object.id
        if id in self.__userObjectTable:
            self.__commonNames[nick] = id
            user_object.addNick(nick)
        else:
            self.__userObjectTable[id] = user_object
            self.__commonNames[nick] = id

    def __iter__(self):
        ## FIXME: probably should iterate over user objects rather than id's ? 
        #         requires more changes to ircstats too
        for uid in self.__userObjectTable.keys():
            yield uid

    def __contains__(self, key):
        return (key in self.__userObjectTable) or (key in self.__commonNames)

    def merge(self, uid1, uid2):
        """Makes UID1 and UID2 refer to the same user object; returns new UID"""
        # FIXME: Not implemented.  Important.
        raise Exception, "Not Implemented"

    def write_yaml(self, yaml_file = 'usernames.yaml'):
        """Write out a yaml file reflecting the current state of the user tables."""
        new_yaml_data = {}
        for key in self.__userObjectTable.keys():
            if key in self.__yaml_data:
                new_yaml_data[key] = self.__yaml_data[key]
            else:
                new_yaml_data[key] = self.yamlifyUserStats(self.__userObjectTable[key])
        
        if os.access(yaml_file, os.F_OK) and os.access(yaml_file, os.W_OK):
            os.rename(yaml_file, yaml_file+'.bak')
        f = open(yaml_file, 'wb')
        yaml.dump(new_yaml_data, f, indent=4)

    def close(self):
        """Write out our data files"""
        self.write_yaml()
        self.__userObjectTable.sync()

    def yamlifyUserStats(self, user_object):
        """Return a data structure conforming to our YAML format for user_object"""
        return { 'real name': '', 'email': [ '' ], 'irc': [str(nick) for nick in user_object.nicks], 'wiki': [ '' ] } 

    def keys(self):
        """Return a list of every UUID we're tracking - lazily"""
        for key in self.__userObjectTable.keys():
            yield key

    def __len__(self):
        """Return the number of unique user objects being tracked."""
        return len(self.__userObjectTable.keys())

    def idToName(self, id):
        """If id is in our database, give a real name if we have one, or else nicks[0]"""
        if id in self.__yaml_data:
            record = self.__yaml_data[id]
            name = record['real name']
            if name != '': return name
        else: return self.__userObjectTable[id].nicks[0]

            

