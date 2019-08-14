# Brick is a modular and expandable chat-bot capable of basic learning and information fetching by API calls.
# Copyright (C) 2015  Bill Ballou

# This file is part of Brick.

# Brick is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# Brick is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Brick.  If not, see <http://www.gnu.org/licenses/>.

import re
import settings
from util import jprint, depunctuate, log
from settings import config, code

def shutup(bag):

    params = re.match('(?:shut(?:[-\s])?up|go\saway)(?:(?:\s+for\s+a\s+(bit|moment|while|min(?:ute)?))|(?:\s+for\s+(\d+)([smh])))?\s*[\.,!]?', bag['msg'], re.I)
    if params:
        
        # Default Value
        dur = config['mutetime']

        # Subjective values
        perm = None
        if params.group(1) == 'bit':
            dur = random.randint( 4 * 60, 8 * 60 )
        elif params.group(1) == 'moment':
            dur = random.randint( 30, 90 )
        elif params.group(1) == 'while':
            dur = random.randint( 30 * 60, 60 * 60)
        elif params.group(1) in ('min', 'minute'):
            dur = 60

        # Exact Values - admin only
        elif params.group(3) == 's':
            dur = int(params.group(2))
            perm = 'op'
        elif params.group(3) == 'm':
            dur = int(params.group(2)) * 60
            perm = 'op'
        elif params.group(3) == 'h':
            dur = int(params.group(2)) * 60 * 60
            perm = 'op'
    
        return { 'dur' : dur, 'permission' : perm }


def unshutup(bag):

    if re.match('(?:un[-\s]?shut[-\s]?up)|(?:come[-\s]?back)\s*[\.,!]?', bag['msg'], re.I):

        # Un-Shutup
        if bag['role'] in ('admin', 'op'):
            return True


def restart(bag):
    return re.match('\s*restart\s*[\.,!]?', bag['msg'], re.I)

def refresh(bag):
    return re.match('\s*refresh\s*[\.,!]?', bag['msg'], re.I)

def cache(bag):

    match = re.match('(un)?cache\s+(.+)$', bag['msg'], re.I)
    if match:
        (mode, index) = match.group(1, 2)

        # Determine mode
        if mode:
            mode = 0
        else:
            mode = 1

        # Get Index
        index = int_index(index)

        return { 'mode' : mode, 'index' : index }

def protect(bag):

    match = re.match('(un)?protect\s+(.+)', bag['msg'], re.I)
    if match:
        (mode, index) = match.group(1, 2)

        # Determine mode
        if mode:
            mode = 0
        else:
            mode = 1

        # Get Index
        index = int_index(index)

        return { 'mode' : mode, 'index' : index }

def protectvar(bag):

    match = re.match('(un)?protect\s+var\s+(\w+)\s*[!\.]?$', bag['msg'], re.I)
    if match:
        (protect, var) = match.group(1, 2)
        if protect:
            protect = 0
        else:
            protect = 1

        return { 'mode' : protect, 'var' : var }


def syllables(bag):
    match = re.match("([\w'\s]+)\s+has\s+(\d+)\s+syllables?\s*[\.,!]?", bag['msg'], re.I)
    if match:
        (subj, syll) = match.group(1, 2)
        syll = int(syll)
        return { 'subj' : subj, 'syll' : syll }


def syllablecount(bag):
    match = re.match('how\s+many\s+syllables\s+(?:does|are\s+in)\s+(.+?)(?:\s+have)?(?:\s*\?)?$', bag['msg'], re.I|re.DOTALL)
    if match:
        return match.group(1)

def query(bag):
    match = re.match('(.+)\s*~=\s*(.+)', bag['msg'], re.I|re.DOTALL)
    if match:
        return { 'subj' : match.group(1), 'key' : match.group(2) }

def lookup(bag):
    match = re.match('lookup\s+(.+)', bag['msg'], re.I|re.DOTALL)
    if match:
        return match.group(1)

def literal(bag):
    match = re.match('literal\s+(.+)', bag['msg'], re.I|re.DOTALL)
    if match:
        return match.group(1)

def last(bag):
    if re.match('what\s+was\s+that\s*\?', bag['msg'], re.I):
        return True

def edit(bag):
    match = re.match('(?:#(\d+)\s+)?sub\s+(.+)\s*=>\s*(.+)$', bag['msg'], re.I)
    if match:
        (key, new, old) = match.group(1, 2, 3)
        new = new.strip()
        old = old.strip()

        # Set index
        if key:
            index = int(key)
        else:
            index = -1

        return { 'index' : index, 'new' : new, 'old' : old }


def delete(bag):
    match = re.match('(?:forget|remove|delete)\s+((?:that)|(?:#\d+))\s*[\.!]?', bag['msg'], re.I)
    if match:

        # Set key
        key = match.group(1)
        return int_index(key)

def alias(bag):
    match = re.match('alias\s+(.+)\s*=>\s*(.+)$', bag['msg'], re.I)
    if match:
        (src, dst) = match.group(1, 2)
        src = src.strip()
        dst = dst.strip()

        return { 'src' : src, 'dst' : dst }

def unalias(bag):
    match = re.match('un-?alias\s+(.+)$', bag['msg'], re.I)
    if match:
        return match.group(1).strip()

def merge(bag):
    match = re.match('merge\s+(.+)\s*=>\s*(.+)$', bag['msg'], re.I)
    if match:
        (src, dst) = match.group(1, 2)
        src = src.strip()
        dst = dst.strip()
        return { 'src' : src, 'dst' : dst }

def version(bag):
    return re.match('(?:what\s+)?version(?:\s+are\s+you)?\s*[\?\.!]?', bag['msg'], re.I)
        
def stats(bag):
    return re.match('(?:stats|status)\s*[!\.\?]?', bag['msg'], re.I)

def listusers(bag):
    return re.match('list\s*users\s*[\.!]?$', bag['msg'], re.I)

def more(bag):
    return re.match('(?:more|next|continue)', bag['msg'], re.I)

def undo(bag):
    return re.match('undo[\s-]*last\s*$', bag['msg'], re.I)

def listvars(bag):
    match = re.match('list\s+var(s)?(?:\s+(\w+))?\s*$', bag['msg'], re.I)
    if match:

        # List all vars
        if match.group(1):
            listvars = True
        else:
            listvars = False

        # List values
        var = match.group(2)
        if var:
            var = depunctuate(var)

        return { 'listvars' : listvars, 'var' : var }

def setconfig(bag):
    match = re.match('(get|list|set|disable|enable|reset)\s+(\w+)(?:\s+(\S+))?\s*$', bag['msg'], re.I)
    if match:
        (mode, key, val) = match.group(1, 2, 3)

        # Normalize
        mode = depunctuate(mode)
        key = depunctuate(key)
        if val:
            val = val.strip()

        return { 'mode' : mode, 'key' : key, 'val' : val }

def promote(bag):
    match = re.match('((?:pro)|(?:de))mote\s+((?:that)|(?:#\d+))\s*[!\.]?$', bag['msg'], re.I)
    if match:
        (mode, key) = match.group(1, 2)

        # Determine mode
        if mode == 'pro':
            mode = 1
        else:
            mode = -1

        # Set key
        key = int_index(key)

        return { 'mode' : mode, 'user' : key }

def addval(bag):
    match = re.match('((?:add)|(?:remove))\s+(?:(?:value)|(?:var))\s+(\w+)\s+(.+)', bag['msg'], re.I)
    if match:
        (mode, var, value) = match.group(1, 2, 3)
        var = depunctuate(var)
        mode = depunctuate(mode)

        return { 'mode' : mode, 'var' : var, 'val' : value }

def remvar(bag):
    match = re.match('(?:forget|remove|delete)\s+var\s+(\w+)\s*$', bag['msg'], re.I)
    if match:
        var = match.group(1)
        var = depunctuate(var)
        return var

def echo(bag):
    match = re.match('echo\s+(.+)$', bag['msg'], re.I)
    if match:
        return match.group(1)

def crash(bag):
    return re.match('crash$', bag['msg'], re.I)

def random(bag):
    return re.match('something\s*random\s*[\.!]?$', bag['msg'], re.I)

def factlookup(bag):

    # Sufficient Length
    if len(bag['msg']) >= config['min_length']:
        return True

    return False

def question(bag):
    match = re.match('(?:what\s+is|what\'s|the|who\s+is)\s+(.+?)[!\.\?]*$', bag['msg'], re.I)
    if match:
        return match.group(1)

def interrogative(bag):
    match = re.match('(how|what|whom?|where|why)\s+does\s+(\S+)\s+(\w+)(?:\s+(.*?))?[\?!\.]*', bag['msg'], re.I)
    if match:
        (inter, name, verb, start) = match.group(1, 2, 3, 4)
        return { 'inter' : inter, 'name' : name, 'verb' : verb, 'start' : start }

def choice(bag):
    match = re.match('(?:choose\s+)?(?:([^,]+?)(?:\s+or|,)\s+)?([^,]+?),?\s+or\s+([^,]+?)\??$', bag['msg'], re.I)

    # Ignore likely "x is y" commands
    if match and not re.match('.+\s+<\w+>\s+.+', bag['msg'], re.I):
        log('MAKING A CHOICE')
        choices = match.group(1,2,3)

        # Eliminate none matches
        choices = [x for x in choices if x is not None]
        return choices

def yesorno(bag):
    if re.match('(?:(?:is|does|can|are)\s+\w+)|(?:.+\?+$)', bag['msg'], re.I):
        if not re.match('(?:where|when|why|how|what|who)|(?:.+\s+<\w+>\s+.+)|(?:.+\s+or\s+.+)', bag['msg'], re.I):
            return True

def remember(bag):
    match = re.match('remember\s+(\S+)\s+(.+)$', bag['msg'], re.I|re.DOTALL)
    if match:
        (name, text) = match.group(1, 2)

        return { 'name' : name, 'text' : text }

def xisy(bag):

    # Hard Match
    match = re.match('(.+)\s+(<\w+>)\s+(.+)', bag['msg'], re.I|re.DOTALL)
    embed = False

    # Soft Match
    if not match:
        match = re.match('(.+?)\s+(is|are|am)(?:\s+also)?\s+([^\?]+)$', bag['msg'], re.I)
        embed = True


    if match:
        (subj, mode, fact) = match.group(1, 2, 3)

        # ignore likely questions
        if subj in ('what', 'where', 'when'):
            return
        
        if embed:
            mode = '<' + mode + '>'

        return { 'subject' : subj, 'mode' : mode, 'factoid' : fact }



# Process a string into an integer index
def int_index(string):

    # String Number
    match = re.match('#(\d+)$', string)
    if match:
        index = int(match.group(1))
        return index

    # 'that'
    elif string.lower() == 'that':
        return -1

    return string