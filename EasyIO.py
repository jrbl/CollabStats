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
"""A collection of wrapper functions to make common I/o operations easy.
"""

# Imports
import sys                        # stdin, stdout, stderr
from datetime import datetime     # datetime.now()


def owrite(msg, tag=''):
    sys.stdout.write(tag+msg)

def owriteln(msg, tag=''):
    owrite(msg+'\n', tag)

def cowrite(msg, tag, test):
    if test: owrite(msg, tag)

def cowriteln(msg, tag, test):
    if test: owriteln(msg, tag)

def ewrite(msg, tag=''):
    sys.stderr.write(tag+msg)

def ewriteln(msg, tag=''):
    ewrite(msg+'\n', tag)

def cewrite(msg, tag, test):
    if test: cewrite(msg, tag)

def cewriteln(msg, tag, test):
    if test: ewriteln(msg, tag)

def VERBOSE_OUT(msg, flag):
    cowriteln(msg, '', flag)

def DEBUG_ERR(msg, flag):
    cewriteln(msg, 'DEBUG: ', flag)

