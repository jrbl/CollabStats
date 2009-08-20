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
"""Answers simple questions from Wikimedia dumps.

FIXME: Uses a DOM parser; should obviously get re-built around SAX
"""

# Imports
import sys
from xml.dom import minidom as md
from datetime import datetime
import re


#### 
# Proposals were in Proposals/ until a certain date, and then they were all supposed to be moved to 
# Proposals:, and most of them were.  But b/c of policy decisions and the way Mediawiki does data
# dumps, we have to cope with the ugly reality
### FIXME: we should actually support this, but more discussion about the right thing needs to happen
dateProposalsChanged = datetime(2009, 8, 3) # XXX: Probably incorrect date; get good one from Eugene

# Classes


# Utility Functions
def getDOM(file = "strategywiki-20090818-pages-meta-history.xml"):
    sys.stderr.write(str(datetime.now()) + " Reading XML Dump into memory...\n")
    dd = md.parse(file)
    assert dd.documentElement.tagName == u"mediawiki"
    sys.stderr.write(str(datetime.now()) + " ...done.\n")
    return dd

def wikiPages(wikiDOM):
    for kid in wikiDOM.childNodes:
        if kid.nodeName == u"#text":
            continue
        elif kid.nodeName == u"siteinfo":
            continue
        elif kid.nodeName == u"page":
            yield kid

def titles_revcounts(pages):
    for page in pages:
        title = page.getElementsByTagName('title')[0].firstChild.nodeValue
        revCount = len(page.getElementsByTagName('revision'))
        yield unicode(title).encode("utf8"), revCount

def pageRevisions(page):
    for rev in page.getElementsByTagName('revision'):
        yield rev

def eventStream(wikiDOM):
    """Returns a list of (datetime, DOM node) pairs suitable for building mappings"""
    times = wikiDOM.getElementsByTagName('timestamp')
    for t in times:
        #dt = datetime.strptime(t.firstChild.nodeValue, "%Y-%m-%dT%H:%M:%SZ")
        dt = datetime.strptime(t.firstChild.nodeValue[:10], "%Y-%m-%d")
        rev = t.parentNode
        pg = t.parentNode.parentNode
        yield (dt, t, rev, pg)

def getElementText(element):
    return element.firstChild.nodeValue.encode("utf8")

def getPageTitleText(page):
    return getElementText(page.getElementsByTagName('title')[0])

def buildEventIndex(event_stream):
    event_index = {}
    for eventTuple in event_stream:
        dt, ts, rev, pg = eventTuple
        if dt not in event_index:
            event_index[dt] = {pg: [(ts, rev)]}
        elif pg not in event_index[dt]:
            event_index[dt][pg] = [(ts, rev)]
        else: 
            event_index[dt][pg].append( (ts, rev) )
    return event_index

def getRevID(revision):
    return getElementText(revision.getElementsByTagName('id')[0])

def hasFirstRev(revlist):
    for rev in revlist:
        if getRevID(rev[1]) == 1:
            return True
    return False

def getLowestRev(revlist):
    low = 9999999999
    for rev in revlist:
        id = getRevID(rev[1])
        if id < low:
            low = id
    return low

def sortedRevs(revlist):
    def cmp(x, y):
        if getRevID(x[1]) < getRevID(y[1]): return -1
        elif getRevID(x[1]) == getRevID(y[1]): return 0
        else: return 1
    return sorted(revlist, cmp)

def getRevEditor(revision):
    revision = revision[1]
    usernames = revision.getElementsByTagName('username')
    ips       = revision.getElementsByTagName('ip')
    if len(usernames) == 0:
        if len(ips) > 0:
            return getElementText(ips[0])
        else:
            return None # should only happen w/ deleted nodes; information loss?
    else:
        return getElementText(usernames[0])

def getRegEditorOnly(revision):
    revision = revision[1]
    usernames = revision.getElementsByTagName('username')
    if len(usernames) == 0:
        return None 
    else:
        return getElementText(usernames[0])

def editorList(revlist, getter = getRevEditor):
    edlist = []
    for rev in revlist:
        editor = getter(rev)
        if editor not in edlist: edlist.append(editor)
    return sorted(edlist)

def summaryCountsByDate(event_index):

    total_pages         = {}
    total_content_pages = {}
    total_proposals     = {}
    registered_users    = {}
    total_edits         = 0

    for date in sorted(event_index.keys()):
        output = [str(date.date())]
        proposal_re    = re.compile("^(Proposal:)|(Proposals/)")
        non_content_re = re.compile("^(User:)|(Talk )|(.+ talk:)")

        proposals_edited     = 0
        new_proposals_today  = 0
        proposal_edits       = 0
        proposal_editors     = 0
        proposal_registered_editors = 0

        for page in sorted(event_index[date].keys()):
            new_flag     = False
            revlist      = event_index[date][page]
            pagename     = getPageTitleText(page)

            # Summary (Philippe) Stats
            if pagename not in total_pages: 
                new_flag = True
                total_pages[pagename] = date
            if new_flag:
                #if (pagename.find("Talk:") != 0) and (pagename.find("User:") != 0):      # XXX: "regular" pages
                if proposal_re.match(pagename):
                    total_proposals[pagename] = date
                elif not non_content_re.match(pagename): 
                    total_content_pages[pagename] = date
            #if new_flag and pagename.find('Proposal') == 0:
            #if new_flag and proposal_re.match(pagename):
            #    total_proposals[pagename] = date
            for editor in editorList(revlist, getRegEditorOnly):
                if editor not in registered_users:
                    registered_users[editor] = date
            total_edits += len(revlist)

            # Proposal Stats
            #if pagename.find('Proposal') == 0:
            if proposal_re.match(pagename):
                proposals_edited += 1
                proposal_edits  += len(revlist)
                if new_flag: new_proposals_today += 1
                proposal_registered_editors += len(editorList(revlist, getRegEditorOnly))
                editors = editorList(revlist)
                proposal_editors += len(editors)
                if None in editors: proposal_editors -= 1

        output.extend( (len(total_content_pages.keys()), len(total_pages.keys()), len(registered_users.keys()), total_edits, len(total_proposals.keys())) )
        output.extend( (proposals_edited, new_proposals_today, proposal_edits, proposal_registered_editors, proposal_editors) )  
        yield output

def getSummaryCSVHeaders():
    """return the names for the header line for a csv file.  Defined below.

        Date: a day.
        Total Content Pages: The total number of pages whose names don't begin with 
            "User" or "Talk".  Should increase monotonically.
        Total Pages: The total number of pages in the wiki.  Should increase 
            monotonically.
        Registered Users: The total count of unique usernames seen in the log. 
            Should increase monotonically.
        Total Edits: The total number of revisions to pages since the dawn of time.  
            Should increase monotonically.
        Total Proposals: The total number of pages whose names begine with "Proposal".
            Should increase monotonically.
        Proposals Edited: The number of pages called "Proposal" which have been 
            edited on Date.
        New Proposals: Number of pages called "Proposal" whose first revision is Date.
        Proposal Edits: The number of edits to pages called "Proposal" on Date.
        Proposal Reg Editors: Count of unique registered users editing pages called 
            "Proposal" on Date.
        Proposal Editors: Count of unique signifiers (usernames and IPs) editing pages
            called "Proposal" on Date.
    """

    output = []
    output.extend( ('Date', 'Total Content Pages', 'Total Pages', 'Registered Users', 'Total Edits', 'Total Proposals') )
    output.extend( ('Proposals Edited', 'New Proposals', 'Proposal Edits', 'Proposal Reg Editors', 'Proposal Editors') )  
    return output

def statsSummary(dumpDOM):
    event_index = buildEventIndex(eventStream(dumpDOM))
    csvOut(summaryCountsByDate(event_index), header=getSummaryCSVHeaders())

def csvOut(iterable, file_obj=sys.stdout, header=None):
    import csv
    csv.register_dialect("ooffice_like", delimiter=',', skipinitialspace=True, lineterminator="\n", quoting=csv.QUOTE_NONNUMERIC)
    if header:
        csv.writer(file_obj, dialect="ooffice_like").writerow(header)
    for collection in iterable:
        csv.writer(file_obj, dialect="ooffice_like").writerow(collection)


# Test Harness
if __name__ == "__main__":
    import optparse    
    usage = "usage: %prog"
    parser = optparse.OptionParser(usage = usage)
    parser.add_option('-s', '--summary', dest="summary_stats", action="store_true", default=False,
                         help="Whole-archive summary stats, including proposal stats")
    
    opts, args = parser.parse_args()

    dumpDOM = getDOM()

    if opts.summary_stats:
        statsSummary(dumpDOM)

    dumpDOM.unlink()
