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

from DictDB import DictDB
from UserStats import UserStats


class UserTable(object):
    """Maps common names to UUIDs and UUIDs to user objects"""

    def __init__(self, mapping_yaml = 'usernames.yaml', user_objects_db = 'contact_stats.pickle', verbose=False):
        """Builds up the initial name mapping tables from YAML data on disk."""
        self.__userObjectTable = {}              # maps ids -> user objects 
        self.__commonNames = {}                  # maps nicks -> ids
        self.__yaml_data = {}                    # maps ids -> common names, other info
        self.last_id = 0
        self.verbose = verbose

        self.__userObjectTable = DictDB(user_objects_db, flag='c', format='pickle', verbose=self.verbose)
        self.__yaml_data = DictDB(mapping_yaml, format='yaml', verbose=self.verbose)

        # Set last_id higher than anything we've seen (necessary with sequential uids, not uuids)
        # XXX: oh my gods, this is crazy.  But at least it's user-editable, I guess?
        user_keys = sorted( self.__userObjectTable.keys() ) or [ 1 ]
        yaml_keys = sorted( self.__yaml_data.keys()       )       or [ 1 ]
        self.last_id = max(user_keys[ len(user_keys)-1 ], 
                           yaml_keys[ len(yaml_keys)-1 ])

        # Ensure all the tables maintain synchrony on data read
        for id in self.__userObjectTable.keys():
            for nick in self.__userObjectTable[id].nicks:
                if nick == '': continue
                self.__commonNames[nick] = id
        for id in self.__yaml_data.keys():
            real_name = self.__yaml_data[id]['real name']
            nicks = self.__yaml_data[id]['irc']
            if real_name != '':
                self.__commonNames[real_name] = id
            if id not in self.__userObjectTable:
                user_object = UserStats( nicks[0], -1, id ) # XXX: should timestamp properly
                for nick in nicks: 
                    if nick == '': continue
                    user_object.addNick(nick)
                self.__userObjectTable[id] = user_object
            for nick in nicks:
                if nick == '': continue
                self.__commonNames[nick] = id
                if nick not in self.__userObjectTable[id].nicks:
                    self.__userObjectTable[id].nicks.append(nick)

    def getID(self):
        """Gets the next number in the ID sequence.  NOT THREAD SAFE"""
        self.last_id += 1
        return self.last_id

    def __getitem__(self, key):
        if key in self.__userObjectTable:
            return self.__userObjectTable[key]
        elif key in self.__commonNames:
            return self.__userObjectTable[ self.__commonNames[ key ] ]
        # Not found.  Perhaps the key is case-sensitive.
        # Try title-casing.  XXX
        key = key.title()
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

    def merge(self, primary, secondary):
        """Dereferences primary and secondary and copies secondary's data to primary."""
        pobj = self[primary]
        pid = pobj.id
        sobj = self[secondary]
        sid = sobj.id

        def biggest(a, b):
            try:
                if len(a) > len(b): return a
                else: return b
            except TypeError:
                return max(a, b)

        try:
            features = list(set(self.__yaml_data[pid].keys() + self.__yaml_data[sid].keys()))
        except KeyError:
            # FIXME: this makes it possible to merge serialized data to freshly created objects.
            # BUT! it only works if the freshly created object is secondary!
            features = self.__yaml_data[pid].keys()

        for feature in features:
            featp = None
            feats = None
            try:
                feats = self.__yaml_data[sid][feature]
            except KeyError:
                continue
            try: 
                featp = self.__yaml_data[pid][feature]
            except KeyError:
                self.__yaml_data[pid][feature] = feats
                continue
            if isinstance(featp, list):
                self.__yaml_data[pid][feature] = list(set(feats + featp))
                continue
            self.__yaml_data[pid][feature] = biggest(feats, featp)

        ## yaml differences
        #for feature in self.__yaml_data[pid].keys():
        #    if isinstance(self.__yaml_data[pid][feature], list):
        #        fnames = set(self.__yaml_data[pid][feature])
        #        for item in self.__yaml_data[sid][feature]:
        #            fnames.add(item)
        #        self.__yaml_data[pid][feature] = list(fnames)
        #    else:
        #        self.__yaml_data[pid][feature] = biggest(self.__yaml_data[pid][feature], 
        #                                                 self.__yaml_data[sid][feature])

        # pickle differences
        candidate = set(filter(None, pobj.nicks))
        for c in filter(None, sobj.nicks):
            candidate.add(c)
        pobj.nicks = sorted(list(candidate))
        pobj.join_times.extend(sobj.join_times)
        pobj.part_times.extend(sobj.part_times)
        for time in sobj.messages:
            pobj.messages[time] = sobj.messages[time]
        for time in sobj.actions:
            pobj.actions[time] = sobj.actions[time]

        # update common names
        for name in pobj.nicks:
            self.__commonNames[name] = pid

        # delete secondary
        try:
            del(sobj)
            del(self.__userObjectTable[sid])
            del(self.__yaml_data[sid])
        except KeyError:
            # NB: see above re: merging fresh objects to serialized ones
            pass

    def write_yaml(self, yaml_file=None):
        """Write out a yaml file reflecting the current state of the user tables."""
        for key in self.__userObjectTable.keys():
            if key not in self.__yaml_data:
                self.__yaml_data[key] = self.yamlifyUserStats(self.__userObjectTable[key])
        self.__yaml_data.sync(yaml_file)

    def clean(self, dirty_list):
        """Go through dirty_list updating list field types in self.__yaml_data"""
        for data_key, yaml_key, addition in dirty_list:
            #print "self.__yaml_data[%s][%s].append(%s) = %s" % (data_key, yaml_key, addition, 
            #                                                   self.__yaml_data[data_key][yaml_key])
            self.__yaml_data[data_key][yaml_key].append(addition)
            #print "self.__yaml_data[%s][%s].append(%s) = %s" % (data_key, yaml_key, addition, 
            #                                                   self.__yaml_data[data_key][yaml_key])

    def close(self, dirty_list = None):
        """Write out our data files"""
        if dirty_list:
           self.clean(dirty_list)
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
        retVal   = self.__userObjectTable[id].nicks[0]
        if id in self.__yaml_data:
            record   = self.__yaml_data[id]
            realname = record['real name']
            wikis    = record['wiki']
            if realname != '': 
                retVal = realname
            elif len(wikis) >= 1 and wikis[0] != '':
                retVal = wikis[0]
        if isinstance(retVal, str):
            return unicode(retVal, "utf-8")
        elif isinstance(retVal, unicode):
            return retVal
        else:
            return unicode(retVal, "utf-8")

            

