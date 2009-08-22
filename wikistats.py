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
import difflib


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

def getElementText(element):
    return element.firstChild.nodeValue.encode("utf8")

def getPageTitleText(page):
    return getElementText(page.getElementsByTagName('title')[0])

def dateTimeStr(dt_string):
    return datetime.strptime(dt_string, "%Y-%m-%dT%H:%M:%sZ")

def dateStrOnly(dt_string):
    return datetime.strptime(dt_string[:10], "%Y-%m-%d")

def eventStream(wikiDOM):
    times = wikiDOM.getElementsByTagName('timestamp')
    for t in times:
        dt = dateStrOnly(t.firstChild.nodeValue)
        rev = t.parentNode
        pg = t.parentNode.parentNode
        yield (dt, t, rev, pg)

def editorStream(wikiDOM):
    editors = wikiDOM.getElementsByTagName('username')
    for e in editors:
        ed = getElementText(e)
        rev = e.parentNode.parentNode
        dt = dateStrOnly(getElementText(rev.getElementsByTagName('timestamp')[0]))
        yield (ed, rev, dt)

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

def buildEditorIndex(editor_stream):
    editor_index = {}
    for editorTuple in editor_stream:
        ed, rev, dt = editorTuple
        if ed not in editor_index:
            editor_index[ed] = [ (dt, rev) ]
        else: 
            editor_index[ed].append( (dt, rev) )
    return editor_index

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

def getRevisionText(revision):
    text_e = revision.getElementsByTagName('text')
    try:
        return getElementText(text_e[0])
    except AttributeError:
        return ""

def getPreviousRevision(revision):
    my_id = getRevID(revision)
    sibs = revision.parentNode.getElementsByTagName('revision')
    def cmp(x, y):
        if getRevID(x) < getRevID(y): return -1
        elif getRevID(x) > getRevID(y): return 1
        else: return 0
    sibs = sorted(sibs, cmp)
    for i in range(len(sibs)):
        if getRevID(sibs[i]) == my_id:
            if i == 0: return None
            return sibs[i -1]
    return None

def getRegEditorOnly(revision):
    revision = revision[1]
    usernames = revision.getElementsByTagName('username')
    if len(usernames) == 0:
        return None 
    else:
        return getElementText(usernames[0])

def diffTexts(a, b):

    ed_counter = 0
    ed_sizes   = []
    sm = difflib.SequenceMatcher(None, a, b)
    for code, i1, i2, j1, j2 in sm.get_opcodes():
        if code == 'equal':
            continue
        ed_counter += 1
        if code == 'delete':
            ed_sizes.append(i2 - i1)
        elif code == 'insert':
            ed_sizes.append(j2 - j1)
        elif code == 'replace':
            if (j2 - j1) >= (i2 - i1):
                ed_sizes.append(j2 - j1)
            elif (j2 - j2) < (i2 - i1):
                ed_sizes.append(i2 - i1)
    return (ed_counter, ed_sizes)

def editorList(revlist, getter = getRevEditor):
    edlist = []
    for rev in revlist:
        editor = getter(rev)
        if editor not in edlist: edlist.append(editor)
    return sorted(edlist)

def countedEditorList(revlist):
    edlist = {}
    for rev in revlist:
        editor = getRegEditorOnly(rev)
        if editor == None: continue
        if editor not in edlist: edlist[editor] = 1
        else: edlist[editor] += 1
    return edlist.items()

def summaryCountsByDate(event_index):

    total_pages         = {}
    total_content_pages = {}
    total_proposals     = {}
    registered_users    = {}
    total_edits         = 0
    new_reg_users       = 0

    for date in sorted(event_index.keys()):
        output = [str(date.date())]
        proposal_re    = re.compile("^(Proposal:)|(Proposals/)")
        non_content_re = re.compile("^(User:)|(Talk )|(.+ talk:)")

        proposals_edited     = 0
        new_proposals_today  = 0
        proposal_edits       = 0
        proposal_editors     = 0
        proposal_registered_editors = 0

        edits_by_pages       = [ ]
        new_pages_today      = [ ]
        authors_today        = {}

        for page in sorted(event_index[date].keys()):
            new_flag     = False
            revlist      = event_index[date][page]
            pagename     = getPageTitleText(page)

            # Summary (Philippe) Stats
            if pagename not in total_pages: 
                new_flag = True
                total_pages[pagename] = date
            if new_flag:
                if proposal_re.match(pagename):
                    total_proposals[pagename] = date
                elif not non_content_re.match(pagename): 
                    total_content_pages[pagename] = date
            for editor in editorList(revlist, getRegEditorOnly):
                if editor not in registered_users:
                    registered_users[editor] = date
                    new_reg_users += 1
            total_edits += len(revlist)

            # Proposal Stats
            if proposal_re.match(pagename):
                proposals_edited += 1
                proposal_edits  += len(revlist)
                if new_flag: new_proposals_today += 1
                proposal_registered_editors += len(editorList(revlist, getRegEditorOnly))
                editors = editorList(revlist)
                proposal_editors += len(editors)
                if None in editors: proposal_editors -= 1

            # Erik's stats Pt. 1
            edits_by_pages.append(len(revlist))
            if new_flag:
                new_pages_today.append(pagename)
            for editor in countedEditorList(revlist):
                if editor[0] in authors_today: authors_today[editor[0]] += editor[1]
                else: authors_today[editor[0]] = editor[1]

        # Erik's stats Pt. 2
        ed_per_pg_tot = sum(edits_by_pages)    
        ed_per_pg_avg = float(len(event_index[date].keys()))/ed_per_pg_tot if ed_per_pg_tot else 0
        eds5_today = [x[0] for x in authors_today.items() if x[1] >= 5]

        output.extend( (len(total_content_pages.keys()), len(total_pages.keys()), len(registered_users.keys()), total_edits, new_reg_users) )
        output.extend( (len(total_proposals.keys()), proposals_edited, new_proposals_today, proposal_edits, proposal_registered_editors, proposal_editors) )  
        output.extend( (ed_per_pg_avg, len(new_pages_today), len(eds5_today), eds5_today) )
        yield output

def editorCounts(editor_index):
    # { ed: [ ( dt, rev ), ( dt, rev ) ... ] }
    
    sys.stderr.write(str(datetime.now()) + " Starting editor-by-editor processing")
    debug_revs2go = sum([len(v) for v in editor_index.values()])
    debug_counter = 0
    debug_2pct = debug_revs2go/50
    for ed in editor_index:
        output = [ ed ]
        revlist = editor_index[ed]

        original_authorship = 0
        edit_counts = [ ]
        edit_sizes = 0

        for dt, rev in revlist:

            if debug_counter % debug_2pct == 0: 
                sys.stderr.write(".")
                sys.stderr.flush()
            debug_counter += 1

            prev = getPreviousRevision(rev)
            if prev == None: 
                prev_text = ''
                original_authorship += 1
            else: prev_text = getRevisionText(prev)
            cur_text = getRevisionText(rev)
            editCount, editSizes = diffTexts(prev_text, cur_text)
            edit_counts.append(editCount)
            edit_sizes += sum(editSizes)

        avg_edit_count_per_revision = float(sum(edit_counts))/len(edit_counts)
        avg_edit_size = float(edit_sizes)/len(edit_counts) 

        output.extend( (len(revlist), original_authorship, avg_edit_count_per_revision, avg_edit_size) )
        yield output
    sys.stderr.write("\n" + str(datetime.now()) + " done.\n")

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
    output.extend( ('Date', 'Total Content Pages', 'Total Pages', 'Registered Users', 'Total Edits', 'New Registered Users', 'Total Proposals') )
    output.extend( ('Proposals Edited', 'New Proposals', 'Proposal Edits', 'Proposal Reg Editors', 'Proposal Editors') )  
    output.extend( ('Edits/Page Today', 'New Pages Today', '# Editors w/5+ Today', 'Editors w/5+ Today') )  
    return output

def getEditorCSVHeaders():
    """return the names for the header line for a csv file.  Defined below.

    Editor: Registered nick of the editor
    Edits: Number of edits since dawn of time
    Authorship: Number of first revisions since dawn of time
    Avg Changes/Rev: Average number of changes made to the text per revision
    Avg Change Size: Average size of changes made to texts, in characters
    """

    output = []
    output.extend( ('Editor', 'Edits', 'Authorship', 'Avg Changes/Rev', 'Avg Change Size') )
    return output

def statsSummary(dumpDOM):
    event_index = buildEventIndex(eventStream(dumpDOM))
    csvOut(summaryCountsByDate(event_index), header=getSummaryCSVHeaders())

def statsEditors(dumpDOM):
    editor_index = buildEditorIndex(editorStream(dumpDOM))
    csvOut(editorCounts(editor_index), header=getEditorCSVHeaders() ) 

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
    parser.add_option('-e', '--editors', dest="editor_stats", action="store_true", default=False,
                         help="Stats broken out on a per-user basis")
    
    opts, args = parser.parse_args()

    dumpDOM = getDOM()

    if opts.summary_stats:
        statsSummary(dumpDOM)
    if opts.editor_stats:
        statsEditors(dumpDOM)

    dumpDOM.unlink()
