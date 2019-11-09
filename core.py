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

# Core Modules
import re
import sys
import time
import random
import twitter
import requests

# Bot Modules
import util
import parse
import groupme
import brickdb
import syllables
import settings
from util import jprint, sq, dq, log
from settings import config, code, source, roles, mods, defaults, forbidden, forbidden_var

# HTTP Interface
http = requests.Session()
# Twitter
t = None
# Groupme
bot = None

# Load Plugins
import plugins
from plugins import *
mods = plugins.__all__
mods.remove('__init__')

# Global Declarations
version = '3.0.3'
cache = {}
var_cache = {}
users = {}
state = {}

# Parses a web request to determine if a valid message was received.
def process(data):

    # Group Filter
    if data['group_id'] != bot.groupid:
        return

    # System Filter
    if data['system']:
        return

    # Trim Data
    data = { x : y for x, y in data.items() if x in ( 'name', 'text', 'user_id' ) }

    # Stamp Time
    data['timestamp'] = time.time()

    # Process Syllables
    data['syll'] = syllables.find(data['text'])

    # Ignore User
    # if data['name'] in config['ignore']:
    #     log('Ignoring post by', repr(data['name']))

    # Not the bot - Process
    if data['name'] != bot.name:
        data['history'] = state['history']
        data = core(data)

    if config['debug']:
        util.debug('Process Result:', data)

    # Outburst
    refresh_outburst()

    # History
    update_history(data)

    # Return response
    if 'response' in data.keys():
        return data['response']
    

# Runs interval based routines
def heartbeat():

    #DEBUG
    if config['debug']:
        util.debug('State:', state)
        util.debug('Time:', time.time())

    # Check if Shutup
    if shutup():
        return

    # Outburst
    resp = outburst()

    # Reminder
    if not resp:
        resp = reminder()

    # Update State
    updateState()

    return resp

# Returns a factoid if a reminder is triggered
def reminder():

    # Check Cooldown
    if time.time() < state['reminder']['reset']:
        return

    # Check Date
    today = util.today(config['timezone'])
    if state['reminder']['day'] != today:
        return

    # Get responses
    resp = fact_query(state['reminder']['post'])
    if resp['code'] != code['success']:
        return

    result = random.choice(resp['result'])
    result = compile_fact(**result)
    lock_reminder()
    return say(bag=fakebag(), **result)

# Triggers cooldown for reminder
def lock_reminder():
    global state

    state['reminder']['reset'] = state['reminder']['cooldown'] * 60 * 60 + time.time()

# Returns a random fact if a set time has elapsed
def outburst():

    # Outburst not set
    if state['outburst'] is None:
        refresh_outburst()

    # Outburst not triggered - offline always triggers
    if state['outburst'] > time.time():
        return

    # Outburst Triggered
    resp = random_fact()

    # Outburst failed
    if resp['code'] != code['success']:
        log("Outburst failed!")
        return

    # Reset Outburst
    refresh_outburst()
    return say(bag=fakebag(), **resp)

# Resets the time for the next outburst
def refresh_outburst():
    global state

    state['outburst'] = time.time() + util.vary(config['outburst'] * 60 * 60, 0.5)


# Generates a fake bag from known users
def fakebag():
    names = [users[x]['name'] for x in users.keys()]
    names.append('Somebody')
    bag = {
        'name' : random.choice(names),
        'to'   : None
    }
    return bag


# Record post to history
def update_history(bag):
    global state

    # Truncate History
    if len(state['history']) >= config['post_history']:
        state['history'] = state['history'][ -(config['post_history'] - 1) : ]

    # Strip Embedded
    if 'history' in bag.keys():
        del bag['history']

    # Record Data
    state['history'].append(bag)

# Performs pre-processing of message content
def prep(bag):

    # Identify Targets
    bag = gettargets(bag)

    # Clean message
    bag['text'] = bag['text'].strip()
    bag['msg'] = bag['msg'].strip()

    # Get User Role
    bag['role'] = getrole(bag)

    # Initialize response
    bag['response'] = None

    return bag


# Determines the target of the message
def gettargets(bag):

    # Determine target
    match = re.match('\s*(\w+)\s*[:,]\s+(.+)$', bag['text'], re.DOTALL)
    if match:
        (bag['to'], bag['msg']) = match.group(1, 2)

    # Unaddressed
    else:
        bag['to'] = None
        bag['msg'] = bag['text']

    # Addressed
    if bag['to'] and bag['to'].lower() == bot.name.lower():
        bag['addressed'] = True
        bag['to'] = bot.name
    else:
        bag['addressed'] = False

    return bag

# Returns role of the user
# Generates new user if required
def getrole(bag):

    # Determine permissions
    if bag['user_id'] in users.keys():

        # Set default permission
        if 'role' not in users[bag['user_id']]:
            users[bag['user_id']]['role'] = 'user'
            bag['role'] = users[bag['user_id']]['role']

    # Create new user
    else:
        users[bag['user_id']] = { 
                            'name'    : bag['name'], 
                            'role'    : 'user',
                            'group'   : bot.groupid,
                            'user_id' : bag['user_id'] }

    # Load permission
    return users[bag['user_id']]['role']


# Check permission
def restricted(req, role):

    # No requirement
    if not req:
        return { 'code' : code['success'] }

    # Verify roles
    if req not in roles or role not in roles:
        log('Invalid Role!')

    # Permission granted
    elif roles.index(req) <= roles.index(role):
        log('Authorization Successful.')
        return { 'code' : code['success'] }

    # Permission denied
    log('Permission Denied!')
    return cached('[permission denied]', code=code['denied'])


# Restart command
def restart(bag):

    # Authorization
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        log(repr('restart'), 'command from', bag['name'], '(' + bag['role'] + ')', 'ignored')
        return auth

    # Restart
    initialize()
    return { 'code' : code['success'], 'response' : 'Ready to Answer All Bells'}

# Refresh command
def refresh(bag):

    # Authorization
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        log(repr('restart'), 'command from', bag['name'], '(' + bag['role'] + ')', 'ignored')
        return auth

    # Restart
    cache_all()
    return { 'code' : code['success'], 'response' : 'Okay $who, cache updated.'}


# Refresh all caches
def cache_all():
    update_vars()
    update_users()
    update_cache()
    update_syllables()


# Literal command
def literal(subj):

    # Get factoids
    resp = fact_query(subj)

    # No result
    if resp['code'] != code['success']:
        return resp

    facts = resp['result']

    # Alias tag
    if util.depunctuate(subj) != facts[0]['subject_lc']:
        resp = "'" + subj + "' => '" + facts[0]['subject'] + "':"
    else:
        resp = "'" + subj + "':"

    # Cached/Protected Tags
    tags = ''
    if facts[0]['cached']:
        tags += '(cached)'
    if facts[0]['protected']:
        tags += '(protected)'
    if len(tags):
        resp += '\n' + tags

    # Make list
    table = makelist(facts, field1='mode', field2='factoid', ids='_id')
    resp += '\n' + table['list']

    return { 'code' : code['success'], 'list' : resp, 'last' : table['last']}

# Returns a formatted list of users in the channel
def userlist():

    # No users
    if not len(users.keys()):
        log('No users found!')
        return cached(code=code['missing'])

    # Make User List
    ulist = ({ 'name' : users[x]['name'], 'role' : users[x]['role'], 'id' : users[x]['user_id'] } for x in users.keys())
    table = makelist(ulist, field1='name', field2='role', ids='id')

    # Post List
    resp = 'Users:\n' + table['list']
    table['last']['source'] = source['userlist']
    return { 'code' : code['success'], 'response' : resp, 'last' : table['last']}

# Returns a formatted list of vars
def varlist(var=None):

    # No vars
    if not len(var_cache):
        log('No vars cached!')
        return cached(code=code['missing'])

    # List values
    if var:

        # Check for valid var
        if var not in var_cache.keys():
            log('Invalid var specified')
            return { 'code' : code['missing'], 'response' : "var: " + sq(var) + " not found" }

        # Make list
        vlist = ({ 'val' : x['val'], 'id' : x['id'] } for x in var_cache[var])
        table = makelist(vlist, field1='val', ids='id')
        table['last']['source'] = source['varlist']

        # Make response
        resp = var + ':\n'
        if var_cache[var][0]['protected']:
            resp += '(protected)\n'
        resp += table['list']

        # Post list
        return { 'code' : code['success'], 'response' : resp, 'last' : table['last']}

    # List Vars
    vlist = []
    for x in var_cache.keys():
        if var_cache[x][0]['protected']:
            row = { 'var' : x, 'protected' : '(p)' }
        else:
            row = { 'var' : x, 'protected' : '' }
        vlist.append(row)

    # Make Var List
    table = makelist(vlist, field1='var', field2='protected')

    # Post List
    resp = 'Vars:\n' + table['list']
    return { 'code' : code['success'], 'response' : resp, 'last' : table['last']}


# Return formatted list of keys
def keylist(key=None):

    # key Specified
    if key:

        # Invalid Key
        if key not in config.keys():
            return cached(code=code['missing'])

        # Return value
        return { 'code' : code['success'], 'response' : key + ': ' + str(config[key]) }

    # Get Keys
    keys = [{ 'key' : a, 'val' : config[a] } for a in config.keys() if a not in mods]

    # Eliminate hidden
    keys = [ a for a in keys if not defaults[a['key']]['hidden'] ]

    # No keys
    if not len(keys):
        log('No keys found!')
        return cached(code=code['missing'])

    # Make List
    table = makelist(keys, field1='key', field2='val')

    # Post List
    resp = 'Keys:\n' + table['list']
    return { 'code' : code['success'], 'response' : resp, 'last' : table['last']}


# Return formatted list of plugins
def pluginlist():

    # Get mods
    plist = []
    for x in mods:
        row = { 'key' : x }
        if not config[x]:
            row['val'] = 'disabled'
        else:
            row['val'] = str(config[x]) + '%'
        plist.append(row)

    # No Plugins
    if not len(plist):
        log('No Plugins Loaded')
        return { 'code' : code['missing'], 'response' : "I'm not running any plugins, $who."}

    # Make List
    table = makelist(plist, field1='key', field2='val')

    # Post List
    resp = 'Plugins:\n' + table['list']
    return { 'code' : code['success'], 'response' : resp, 'last' : table['last']}

# What was That command
def whatwasthat():

    # Get Last
    last = getlast()
    if last['code'] != code['success']:
        return last
    
    # Recall internal
    if last['source'] == source['internal']:
        return { 'code' : code['success'], 'response' : last['response'], 'last' : last }

    # Recall Database Query
    if last['source'] in (source['cached'], source['database']):
        doc = brickdb.fetch(last['id'])

        # Recall invalid
        if doc['code'] != code['success']:
            log("doc " + repr(state['trace']['id']) + " not found!")

            # Missing Cached Item
            if last['source'] == source['cached']:
                update_cache()
            return cached(code=doc['code'])

        # Recall Successful
        log('Recalled post', repr(last['id']))
        doc = doc['result']

        # Recall
        resp = "That was '" + doc['subject'] + "' " + doc['mode'] + " '" + doc['factoid'] + "'"

        # Append variables
        for var, val in zip(last['var'], last['val']):
            resp += "\n'" + var + "' => '" + val + "'"

        # Valid Recall
        return { 'code' : code['success'], 'response': resp, 'last' : last }

    # invalid trace
    log('No valid trace')
    return cached(code=code['missing'])


# Remove command
def remove(index, bag):

    # Get doc
    doc = getlast(index)
    if doc['code'] != code['success']:
        doc['trace'] = False
        return doc
    
    # Delete variable value
    if doc['source'] == source['varlist']:
        return remvalue(doc['id'], bag)

    # Delete user
    if doc['source'] == source['userlist']:
        return remuser(doc['id'], bag)

    # Delete factoid
    if doc['source'] in ( source['list'], source['database'] ):
        return remfact(doc['id'], bag)

    # Invalid
    return say(bag=bag, trace=False, **cached())


# Returns a status string
def status_string():

    stats = status()

    # Version
    resp = 'I am version ' + stats['version'] + '.  '

    # Up-Time
    resp += "I've been awake for " + stats['uptime'] + '.  '

    # X things about Y subjects
    resp += 'I now know ' + str(stats['facts']) + ' things about ' + str(stats['subjects']) + ' subjects.  '

    # X objects carrying Y of them

    # I know of X people in this channel
    resp += 'I know of ' + str(stats['users']) + ' users in this channel.  '

    # Being quiet right now, but I'll be back in about X
    if shutup():
        if state['timeout'] > 0:
            resp += "I am being quiet right now, but I'll be back in about " + util.string_time(state['timeout'] - time.time())
        else:
            resp += "I am being quiet right now.  "

    return resp


# Returns status data
def status():

    # Gather stats
    stats = { 
        'version'  : version,
        'uptime'   : util.string_time(time.time() - state['uptime']),
        'facts'    : fact_count(),
        'subjects' : subj_count(),
        'users'    : len(users.keys())}

    # Gather post history
    max_posts = 3
    history = state['history']
    if len(history) > max_posts:
        history = history[:max_posts - 1]

    return stats


# Return the next page in the current list
def iterate():

    # Iterate bookmark
    bookmark = state['trace']['bookmark'] + 1
    if bookmark >= len(state['trace']['pages']):
        bookmark = 0

    # Update trace
    last = state['trace']
    last['bookmark'] = bookmark

    # Post next page
    return { 'code' : code['success'], 'response' : state['trace']['pages'][bookmark], 'last' : last }


# Processes addressed commands
def commands(bag):

    # Shutup
    resp = parse.shutup(bag)
    if resp:
        auth = restricted(resp['permission'], bag['role'])
        if auth['code'] == code['success']:
            shutup(resp['dur'])
            return say("Okay, $who, I'll be back later", bag)
        else:
            return say(bag=bag, **auth)


    # Come Back - op only
    if parse.unshutup(bag):
        if shutup() and restricted('op', bag['role'])['code'] == code['success']:
            shutup(0)
            log('Timeout ended by', bag['name'])
            return say("Okay, $who", bag)


    # Restart - admin only
    if parse.restart(bag):
        resp = restart(bag)
        return say(bag=bag, **resp)


    # Cache/UnCache - op only
    match = parse.cache(bag)
    if match:

        # Get subj
        if type(match['index']) is int:
            doc = getlast(match['index'], fulldoc=True)
            if doc['code'] == code['success']:
                subj = doc['doc']['subject_lc']
            else:
                return say(bag=bag, **doc)
        else:
            subj = match['index']

        # Set protection
        if match['mode']:
            protect_mode = 1
        else:
            protect_mode = None

        # Update Cache values
        resp = tag_facts(subj, bag, cache_mode=match['mode'], protect_mode=protect_mode)
        return say(bag=bag, **resp)

    # Protect/Unprotect var - op only
    match = parse.protectvar(bag)
    if match:

        # Update Protect values
        resp = protect_var(match['mode'], match['var'], bag)
        return say(bag=bag, **resp)

    # Protect/Unprotect - op only
    match = parse.protect(bag)
    if match:

        # Get subj
        if type(match['index']) is int:
            doc = getlast(match['index'], fulldoc=True)
            if doc['code'] == code['success']:
                subj = doc['doc']['subject_lc']
            else:
                return say(bag=bag, **doc)
        else:
            subj = match['index']

        # Update Cache values
        resp = tag_facts(subj, bag, protect_mode=match['mode'])
        return say(bag=bag, **resp)

    # Syllables
    match = parse.syllables(bag)
    if match:

        # Update Syllables
        resp = add_syllables(match['subj'], match['syll'], bag)
        return say(bag=bag, **resp)


    # How many syllables
    subj = parse.syllablecount(bag)
    if subj:

        # Get syllables
        count = syllables.find(subj)

        # Generate Response
        plural = 's'
        if count == 1:
            plural = ''
        resp = '$who, "' + subj + '" has ' + str(count) + ' syllable' + plural
        return say(resp, bag=bag)

    # Query - Returns response limited by a key phrase
    match = parse.query(bag)
    if match:

        # Query Facts
        resp = query(match['subj'], match['key'])

        # Failure
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)

        response = []
        for x in resp['result']:
            response.append(compile_fact(**x))

        # Select Response
        resp = random.choice(response)

        # Return Response
        return say(bag=bag, **resp)

    # Lookup
    subj = parse.lookup(bag)
    if subj:

        # Lookup Facts
        resp = lookup('fact', subj)

        # Failure
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)

        # Make list
        table = makelist(resp['result'], field1='subject', field2='mode', field3='factoid', ids='_id')
        resp = '"' + subj + '":\n' + table['list']

        # Post list
        return say(resp, bag=None, last=table['last'])


    # Literal
    subj = parse.literal(bag)
    if subj:
        resp = literal(subj)
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)
        return say(resp['list'], bag=None, last=resp['last'])


    # What was that?
    if parse.last(bag):
        resp = whatwasthat()

        # Failed
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)

        # Success
        return say(bag=None, **resp)


    # Edit - #[key] sub [new] => [old]
    resp = parse.edit(bag)
    if resp:
        index = resp['index']
        new = resp['new']
        old = resp['old']

        # Edit factoid
        resp = edit_fact(new, old, bag, index=index)
        return say(bag=bag, **resp)

    # Delete
    index = parse.delete(bag)
    if index is not None:

        # Remove target
        resp = remove(index, bag)
        return say(bag=bag, **resp)

    # Alias
    match = parse.alias(bag)
    if match:

        # Alias
        resp = alias(match['src'], match['dst'], bag)
        return say(bag=bag, **resp)


    # Unalias - Admin Only
    match = parse.unalias(bag)
    if match:

        # Unalias
        resp = unalias(match, bag)
        return say(bag=bag, **resp)


    # Merge - Admin only - Permanent
    match = parse.merge(bag)
    if match:
        
        # Merge
        resp = merge(match['src'], match['dst'], bag)
        return say(bag=bag, **resp)

    # Version
    if parse.version(bag):
        log('Version Requested')
        return say('$who, I am version ' + version, bag=bag)

    # Status
    if parse.stats(bag):
        log('Status requested')
        return say(status_string())

    # List users
    if parse.listusers(bag):

        resp = userlist()
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)
        return say(bag=None, **resp)

    # List vars
    match = parse.listvars(bag)
    if match:
        
        # List vars
        if match['listvars']:
            resp = varlist()

        # List Values
        else:
            resp = varlist(match['var'])


        # Response
        if resp['code'] != code['success']:
            return say(bag=bag, **resp)
        return say(bag=None, **resp)


    # Iterate through a list
    if parse.more(bag) and state['trace']:
        if 'pages' in state['trace'].keys() and len(state['trace']['pages']) > 1:
            resp = iterate()
            return say(bag=None, **resp)
            

    # Change Config
    match = parse.setconfig(bag)
    if match:

        # Get key value
        if match['mode'] in ('get', 'list'):

            # Get list of keys
            if match['key'] == 'keys':
                resp = keylist()
                if resp['code'] != code['success']:
                    return say(bag=bag, **resp)
                return say(bag=None, **resp)

            # Get Plugin list
            if match['key'] == 'plugins':
                resp = pluginlist()
                if resp['code'] != code['success']:
                    return say(bag=bag, **resp)
                return say(bag=None, **resp)

            # Get value
            if match['key'] in config.keys():
                resp = keylist(match['key'])
                if resp['code'] != code['success']:
                    return say(bag=bag, **resp)
                return say(bag=bag, **resp)

        # Set Key Value
        resp = changekey(match['key'], match['mode'], match['val'], bag)
        return say(bag=bag, **resp)

    # Promote/Demote user
    match = parse.promote(bag)
    if match:
        resp = promote(match['mode'], match['user'], bag)
        return say(bag=bag, **resp)

    # Add Value
    match = parse.addval(bag)
    if match:

        # Add value
        if match['mode'] == 'add':
            resp = addvalue(match['var'], match['val'], bag)
            return say(bag=bag, **resp)

    # Remove var - Op only
    match = parse.remvar(bag)
    if match:
        resp = remvar(match, bag)
        return say(bag=bag, **resp)                

    # Undo Last
    if parse.undo(bag):
        resp = undo(bag)
        return say(bag=bag, **resp)

    # Refresh All Caches
    if parse.refresh(bag):
        resp = refresh(bag)
        return say(bag=bag, **resp)

    # Development Commands
    if config['devmode']:
        resp = development(bag)
        if resp:
            return say(bag=bag, **resp)
    

# Development Commands
def development(bag):

    #Authenticate
    auth = restricted('admin', bag['role'])
    if auth['code'] != code['success']:
        return

    # Echo
    match = parse.echo(bag)
    if match is not None:
        return { 'code' : code['success'], 'response' : match }

    # Crash
    if parse.crash(bag):
        sys.exit('Crash initiated by ' + bag['name'])
        return


# Functions requiring addressing
def addressed(bag):

    # Addressed only
    if not bag['addressed']:
        return []

    # Initialize response list
    response = []

    # Something Random
    if parse.random(bag):
        resp = random_fact()
        if resp['code'] == code['success']:
            response.append(resp)

    # Make a choice
    choices = parse.choice(bag)
    if choices:
        resp = choice(choices)
        if resp['code'] == code['success']:
            response.append(resp)

    # Yes or No Question
    if parse.yesorno(bag):
        response.append(cached('[yes or no]'))

    # Remember Quote
    match = parse.remember(bag)
    if match:
        resp = remember(match['name'], match['text'], bag)
        if 'response' in resp.keys():
            response.append(resp)

    # X is Y
    match = parse.xisy(bag)
    if match:

        resp = xisy(match['subject'], match['mode'], match['factoid'], bag)
        if 'response' in resp.keys():
            response.append(resp)

    # Response
    return response


# Process Messages
def core(bag):
    
    ##########
    # Set up #
    ##########

    # Pre-Process Post
    bag = prep(bag)

    # Update User
    update_user(bag['user_id'], bag['name'])

    # Log Message
    if bag['to']:
        log_tag = "=> (" + bag['to'] + ")"
    else:
        log_tag = ''
    log('Processing Message -', bag['name'], '(' + bag['role'] + ')', log_tag + ':', bag['msg'])

    # Check if shutup - admin override
    if shutup() and (bag['role'] not in ('admin, op') or not bag['addressed']):
        log('Message Ignored - Currently Muted')
        return bag

    ############
    # Commands #
    ############

    # Commands must be addressed
    if bag['addressed']:
        bag['response'] = commands(bag)
        
    # Command responses take priority
    if bag['response']:
        return bag


    ############
    # Factoids #
    ############

    # Ignore long un-addressed posts
    if not bag['addressed']:
        if len(bag['msg']) > config['max_length']:
            log("Lengthy post ignored - " + str(len(bag['msg'])) + ' characters.')
            return bag

    # Initialize response list
    response = []

    # Addressed functions
    response += addressed(bag)
    if not len(response):

        # Factoid lookup
        if parse.factlookup(bag) or bag['addressed']:
            resp = fact_query(bag['msg'])

            # Success
            if resp['code'] == code['success']:
                for x in resp['result']:
                    response.append(compile_fact(**x))

        # Answer a Question
        match = parse.question(bag)
        if match:
            resp = fact_query(match)

            # Success
            if resp['code'] == code['success']:
                for x in resp['result']:
                    response.append(compile_fact(**x))

        # Interrogative
        # match = parse.interrogative(bag)
        # if match:
        #     resp = interrogative(**match)
        #     if resp['code'] == code['success']:
        #         for x in resp['result']:
        #             response.append(compile_fact(**x))

        # Plugins
        response += plugins(bag)

        # Debugging
        if config['debug']:
            util.debug('Response List:', response)

    # No Response
    if not len(response):
        if bag['addressed']:
            bag['response'] = say(bag=bag, **cached())
        return bag

    # Select Response
    resp = random.choice(response)

    # Return Response
    bag['response'] = say(bag=bag, **resp)
    return bag


# Process Plugins
def plugins(bag):

    response = []
    for mod in mods:

        # Trigger Probability
        if random.randint(0, 100) <= config[mod]:

            try:
                result = eval(mod + ".main(bag, config)")

                # Function Call
                if type(result) == dict:
                    if 'call' in result.keys():

                        # Get Tweets
                        if result['call'] == 'twitter':
                            tweets = gettweets(result['username'])
                            result = eval(mod + ".recall(bag, config, tweets)")

                        # Get Vars
                        elif result['call'] == 'getvar':
                            values = getvalues(result['var'])
                            result = eval(mod + ".recall(bag, config, values)")
            
            # Catch Plugin Errors
            except:
                if config['offline']:
                    raise
                else:
                    log('Plugin "' + mod + '" encountered an error -', sys.exc_info()[0])
                    continue

            # Dictionary
            if type(result) == dict:
                keys = result.keys()

                # Learn Value
                if 'addval' in keys:
                    resp = addvalue(result['addval']['var'], result['addval']['val'], bag)
                    if resp['code'] == code['success'] and 'success' in result['addval'].keys():
                        response.append({ 'response' : result['addval']['success'], 'last' : resp['last'] })
                    elif resp['code'] == code['success']:
                        result['last'] = resp['last']

                # Learn Fact
                if 'learn' in keys:
                    resp = new_fact(result['learn']['subj'], result['learn']['mode'], result['learn']['fact'], bag)
                    if resp['code'] == code['success'] and 'success' in result['learn'].keys():
                        response.append({ 'response' : result['learn']['success'], 'last' : resp['last'] })
                    elif resp['code'] == code['success']:
                        result['last'] = resp['last']

                # Lookup
                if 'lookup' in keys:
                    resp = fact_query(result['lookup'])
                    if resp['code'] == code['success']:
                        for x in resp['result']:
                            response.append( compile_fact(**x) )

                # Response
                if 'msg' in keys:
                    resp = { 'response' : result['msg'] }
                    if 'last' in keys:
                        resp['last'] = result['last']
                    response.append(resp)

            # String
            if type(result) is str:
                response.append({ 'response' : result })

            # List
            elif type(result) is list:
                for x in result:
                    if type(x) is str:
                        x = { 'response' : x }
                    response.append(x)

    return response


# Process an X is Y command
def xisy(subject, mode, factoid, bag):

    # Depunctuate
    subject_lc = util.depunctuate(subject)

    # You are
    if subject_lc == 'you' and mode == '<are>':
        subject = bot.name
        subject_lc = util.depunctuate(subject)
        mode = '<is>'

    # I am
    if subject_lc == 'i' and mode == '<am>':
        subject = bag['name']
        subject_lc = util.depunctuate(subject)
        mode = '<is>'

    # Add Factoid
    resp = new_fact(subject, mode, factoid, bag)
    if resp['code'] != code['success']:
        return resp

    return { 'response' : resp['response'], 'last' : resp['last']}


# Remember a quote from a user
def remember(name, text, bag):

    # Message history
    resp = bot.history()

    # Failed
    if resp['code'] != code['success']:
        return cached(code=resp['code'])

    # Success
    messages = resp['result']

    # Match quote
    for message in messages:
        if re.search(name, message['name'], re.I) and re.search(text, message['text'], re.I):
            name = message['name']
            text = message['name'] + ': "' + message['text'] + '"'
            break

    # No Match
    else:
        log("No matching quote found")
        return { 'code' : code['missing'], 'response' : "Sorry, $who, I don't remember what " + name + " said." }

    # Normalize
    name_lc = util.depunctuate(name)

    # No Bot Quotes
    if name_lc == util.depunctuate(bot.name):
        log("Attempt to quote the bot denied")
        return { 'code' : code['denied'], 'response' : "Sorry, $who, you aren't allowed to quote me." }

    # No Self Quotes
    if name_lc == util.depunctuate(bag['name']):
        log("Attempt to quote self denied")
        return { 'code' : code['denied'], 'response' : "$who, please don't quote yourself." }

    # Remember
    resp = new_fact( name + ' quote', '<reply>', text, bag )

    # Failed
    if resp['code'] != code['success']:
        return resp

    # Set response
    return { 'response' : "Okay, " + bag['name'] + ", remembering " + text, 'last' : resp['last'] }
       


# Answers an interrogative
# Disabled - Depricated in v3
# def interrogative(inter=None, name=None, verb=None, start=None):

#     # Conjugate to 3rd person singular
#     verb = pattern.en.conjugate(verb, '3sg')

#     # Log progress
#     log = 'Looking up "' + name + '" (' + verb + ')'
#     if start:
#         log += ' "' + start + "\""
#     log(log)

#     # Find matches
#     resp = verb_query(name, verb, start)
#     return resp


# Makes a choice between options in a list
def choice(choices):

    # Add cached choice
    choices.append(None)

    # Decide
    choice = random.choice(choices)


    # Response
    if choice:
        resp = { 'response' : choice }
    elif len(choices) > 3:
        resp = cached('[choice 3]')
    else:
        resp = cached('[choice 2]')

    resp['code'] = code['success']
    return resp


# returns values for a given var
def getvalues(var):

    if var not in var_cache.keys():
        return

    values = []
    for x in var_cache[var]:
        values.append(x['val'])
    return values

# Add Variable Value
def addvalue(var, value, bag):

    # Check for forbidden vars
    if var in forbidden_var:
        log('Forbidden variable - Permission Denied')
        return cached("[permission denied]", code=code['denied'])

    protected = 0

    # Var exists
    if var.lower() in var_cache.keys():

        # Check existing values
        for val in var_cache[var]:

            # Duplicate Value
            if val['val'] == value:
                log('Duplicate value found')
                return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

            # Check Protection
            if val['protected']:
                protected = 1

        # Check permission
        if protected:
            auth = restricted('op', bag['role'])
            if auth['code'] != code['success']:
                log('Var protected - permission denied')
                return auth

    # add value
    payload = makevar(var, value, bag['user_id'], protected)
    resp = brickdb.post_docs(payload)

    # Failure
    if resp['code'] != code['success']:
        return resp

    # Undo Record
    setundo(user=bag['user_id'], 
            docs=payload,
            update=resp['result'],
            delete=True, 
            response="Okay $who, forgot " + var + " " + sq(value),
            command='cache_vars')

    # Success
    log("Added new value " + sq(value) + " to var " + sq(var))

    # update cache
    update_vars(varid=resp['result'][0]['id'], var=var, val=value, protected=protected)

    # Response
    last = { 'id' : [resp['result'][0]['id']], 'source' : source['varlist'] }
    return { 'code' : code['success'], 'response' : "Okay, $who, learned new " + var + " " + sq(value), 'last' : last }


# Remove Variable Value
def remvalue(docid, bag):

    # Check permission
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        return auth

    # Remove value
    resp = brickdb.delete_docs(docid)
    
    # Failure
    if resp['code'] != code['success']:
        return resp

    # Undo Record
    old = resp['old'][0]
    var = old['var']
    value = old['value']
    setundo(user=bag['user_id'], 
            docs=old, 
            delete=False, 
            response="Okay $who, un-forgot " + var + " " + sq(value),
            command='cache_vars')
    update_vars()
    return { 'code' : code['success'], 'response' : "Okay, $who, forgot " + var + " '" + value + "'" }


# Remove var and update cache
def remvar(var, bag):

    # Check permission
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        return auth

    # Get docs
    resp = brickdb.query('vars', key=var, fulldocs=True)

    # Failed
    if resp['code'] != code['success']:
        return resp

    # Success
    docs = resp['result']

    # Missing
    if not len(docs):
        log("Var not found")
        return cached(code=code['missing'])

    # Delete docs
    old = docs.copy()
    resp = brickdb.delete_docs(docs, undo=False)

    # Failed
    if resp['code'] != code['success']:
        return resp

    # Success
    log("var '" + var + "' removed")

    # Set Undo
    setundo(user=bag['user_id'],
            docs=old,
            delete=False,
            response="Okay $who, un-forgot var " + sq(var),
            command='cache_vars')
    update_vars()
    return { 'code' : code['success'], 'response' : "Okay, $who, removed var " + sq(var) }


# Fills a variable with a case matched string
# Selects string randomly if list is provided
def fill(var, txt, msg):

    if type(txt) == str:
        sub = txt

    newvars = []
    newvals = []

    while True:
        match = re.search('\$(' + var + '\+?)', msg, re.I)
        if match is not None:
            if type(txt) == list:
                sub = random.choice(txt)
            if not match.group(1).islower():
                sub = setcase(sub, match.group(1) )
            msg = re.sub('\$' + var + '\+?', sub, msg, 1, re.I)
            newvars.append("$" + match.group(1))
            newvals.append(sub)
        else:
            break

    return msg, newvars, newvals

# Returns the number of known facts
def fact_count():

    # Get Count
    resp = brickdb.query('nonalias_count')

    # Failed
    if resp['code'] != code['success']:
        return resp

    # Return count
    return resp['result'][0]['value']

# Returns the number of known subjects
def subj_count():

    # Get subjects
    resp = brickdb.query('nonalias_count', group=True, group_level=1)

    # Failed
    if resp['code'] != code['success']:
        return resp

    return len(resp['result'])


# Returns a random response from various sources
# Excludes cached factoids 
def random_fact(include_cached=False):

    # Select Fact
    count = fact_count()
    choice = random.randint(0, count - 1)
    resp = brickdb.query('nonalias', fulldocs=True, limit=1, skip=choice)

    # Failed
    if resp['code'] != code['success']:
        return resp

    # Generate Response
    result = resp['result'][0]
    return compile_fact(**result)
   

# Returns true if muted
# Increases mute time by duration specified in seconds
# Negative numbers mute permanently, 0 unmutes
def shutup(dur=None):
    global state

    if dur:

        # Mute
        if dur < 0:
            state['timeout'] = -1
            log('Muting')
            return True

        # Unmute
        if dur == 0:
            state['timeout'] = 0
            log('Unmuting')
            return False

        # Increase Mute
        if state['timeout'] < time.time():
            state['timeout'] = time.time() + dur
        else:
            state['timeout'] += dur
        log('Shutting up for ' + util.string_time(state['timeout'] - time.time()))
        return True

    # Timeout check
    if state['timeout'] > time.time() or state['timeout'] < 0:
        return True

    return False

# Process an alias command
def alias(src, dst, bag):

    # Normalize
    src_lc = util.depunctuate(src)
    dst_lc = util.depunctuate(dst)

    # Check existing facts
    resp = fact_query(src_lc, False)

    # No docs - create
    if resp['code'] == code['missing']:

        # New Alias Doc
        postresp = new_fact(src, '<alias>', dst_lc, bag)

        # Failure
        if postresp['code'] != code['success']:
            return postresp

    # Existing docs
    if resp['code'] == code['success']:

        # Alias Check
        facts = resp['result']
        for x in facts:
            if x['mode'] == '<alias>':

                # Existing Match
                if x['factoid'] == dst_lc:
                    log("'" + src + "' already aliased to '" + dst + "'")
                    return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

                # Existing Alias - Update
                old = x.copy()
                x['factoid'] = dst_lc
                resp = brickdb.update_docs(x, undo=False)
                if resp['code'] != code['success']:
                    log('Alias failed!')
                    return resp

                # Set Undo
                setundo(user=bag['user_id'], 
                        docs=old,
                        update=resp['result'],
                        response="Okay $who, alias restored.")

            # Existing factoid
            else:
                log('Alias failed - Existing factoid found')
                return { 'code' : code['conflict'], "response" : "Sorry, $who, there is already a factoid for '" + src + "'" }
            
    log("'" + src + "' aliased to '" + dst + "'")
    return { 'code' : code['success'], 'response' : "Okay, $who" }


# Process unalias command
def unalias(subj, bag):

    # Check existing facts
    resp = fact_query(subj, False)

    # Missing
    if resp['code'] == code['missing']:
        log("No factoid found for '" + match + "'")
        return resp

    # Isolate
    fact = resp['result'][0]

    # Existing Factoid
    if fact['mode'] != '<alias>':
        log("'" + match + "' is not aliased")
        return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

    # Remove Alias
    else:
        resp = remfact(fact['_id'], bag)
        return resp


# Returns the common properties of a set of facts
def common(docs, verify=True, autofix=False):

    # Get common properties
    common = {
    'subject_lc' : docs[0]['subject_lc'],
    'cached'     : docs[0]['cached'],
    'protected'  : docs[0]['protected'],
    'alias'      : False
    }

    # Get Alias mode
    if docs[0]['mode'] == '<alias>':
        common['alias'] = True

    # Verify docs
    if verify:
        for doc in docs:

            # Subject Check
            if doc['subject_lc'] != common['subject_lc']:
                log('Subject is not common! - "' + doc['subject_lc'] + '"')
                return cached(code=code['conflict'])

            # Cache Check
            if doc['cached'] != common['cached']:
                log('Cache mismatch! - "' + doc['subject_lc'] + '"')
                return cached(code=code['conflict'])

            # Protect Check
            if doc['protected'] != common['protected']:
                log('Protection mismatch! - "' + doc['subject_lc'] + '"')
                return cached(code=code['conflict'])

            # Alias Check
            if doc['mode'] == '<alias>' and not common['alias']:
                log('Mode mismatch! - "' + doc['subject_lc'] + '"')
                return cached(code=code['conflict'])
            if doc['mode'] != '<alias>' and common['alias']:
                log('Mode mismatch! - "' + doc['subject_lc'] + '"')
                return cached(code=code['conflict'])


    return { 'code' : code['success'], 'result' : common }

# Process Merge command
def merge(src, dst, bag):

    # Authentication
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        return auth

    log("Attempting to Merge: " + sq(src) + " => " + sq(dst))

    # Normalize
    dst_lc = util.depunctuate(dst)
    src_lc = util.depunctuate(src)

    # Get Source Facts
    resp = fact_query(src, alias=False)
    if resp['code'] != code['success']:
        return resp
    srcfacts = resp['result']

    # Get Destination Facts
    resp = fact_query(dst_lc, alias=False, properties=True)

    # Failure
    if resp['code'] not in (code['success'], code['missing']):
        return resp    

    # Destination Exists
    if resp['code'] != code['missing']:
        dstfacts = resp['result']
        dstprop  = resp['properties']

        # Prevent merging with Alias
        if dstprop['alias']:
            log('Unable to merge with alias factoid!')
            return { 'code' : code['conflict'], 'response' : "Sorry, $who, but " + sq(dst) + " is an alias for " + sq(dstfacts[0]['factoid']) + '.' }

    # Default Configuration
    else:
        dstfacts = []
        dstprop = {
            'cached'     : 0,
            'protected'  : 0,
            'subject_lc' : dst_lc
            }
    
    # Modify Source Facts
    update = srcfacts.copy()
    for fact in update:
    
        # Existing Alias check
        if fact['mode'] == '<alias>' and fact['subject_lc'] == dst_lc:
            log("'" + src + "' already aliased to '" + dst + "'")
            return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

        # Remove Alias
        elif fact['mode'] == '<alias>': 
            fact['_deleted'] = True
            continue

        for x in dstfacts:

            # Remove Duplicates
            if x['factoid'] == fact['factoid']:
                fact['_deleted'] = True
                break
        
        # Move Factoid
        else:
            fact['cached']     = dstprop['cached']
            fact['protected']  = dstprop['protected']
            fact['subject']    = dstprop['subject_lc']
            fact['subject_lc'] = dstprop['subject_lc']

    # Create new Alias
    payload = makefact(src, '<alias>', dst_lc, bag['user_id'], dstprop['protected'], dstprop['cached'])
    resp = brickdb.post_docs(payload)

    # Failure
    if resp['code'] != code['success']:
        log("Merge Failed!")
        return { 'code' : code['failed'], 'response' : "Sorry, $who, I am unable to do that right now." }

    # Make undo record
    payload['_id']  = resp['result'][0]['id']
    payload['_rev'] = resp['result'][0]['rev']
    payload['_deleted'] = True
    undo_doc = srcfacts
    undo_doc.append(payload)

    # Post updated docs
    resp = brickdb.update_docs(update, undo=False)
    if resp['code'] != code['success']:
        log('Merge Failed!')
        return { 'code' : resp['code'], 'response' : "Sorry, $who, I am unable to do that right now." }

    # Success
    log(sq(src) + " aliased to " + sq(dst))
    log('Merge complete')

    # Set Undo
    setundo(user=bag['user_id'], 
            docs=undo_doc,
            update=resp['result'],
            response="Okay $who, factoids unmerged.")

    return { 'code' : code['success'], 'response' : "Okay, $who" }

# Process an edit command
def edit_fact(new, old, bag, index=None, doc=None):

    # Check parameters
    if not doc and index is None:
        return cached(code=code['missing'])

    # Get doc
    if not doc:
        doc = getlast(index, fulldoc=True)
        if doc['code'] != code['success']:
            return doc
        doc = doc['doc']

    # Self-editing protection
    self = selfcheck(doc['subject'], bag['name'])
    if self['code'] != code['success']:
        auth = restricted('admin', bag['role'])
        if auth['code'] != code['success']:
            return auth

    # Check permissions - admin, op, or owner
    if doc['added_by'] != bag['user_id']:
        auth = restricted('op', bag['role'])
        if auth['code'] != code['success']:
            return auth

    # Edit Factoid
    undo_doc = doc.copy()
    doc['factoid'] = re.sub(old, new, doc['factoid'])
    resp = brickdb.update_docs(doc, undo=False)

    # Failure
    if resp['code'] != code['success']:
        return { 'code' : resp['code'], 'response' : "Sorry, $who, I am unable to update that right now." }

    # Success
    setundo(user=bag['user_id'], 
            docs=undo_doc,
            update=resp['result'],
            response="Okay $who, factoid reverted.")
    return { 'code' : code['success'], 'response' : "Okay, $who. Factoid updated." }
    

# Adds syllable entry to database and cache
def add_syllables(subj, syll, bag):

    # Word count
    if re.search('\w+\s+\w+', subj, re.I):
        log('Multiple words detected in syllable command')
        return { 'code' : code['failed'], 'response' : "Sorry, $who, I can only learn syllables for one word at a time." }
    
    # Check Cache
    elif subj.lower() in syllables.syllcache.keys() and syllables.syllcache[subj.lower()] == syll:
        log("'" + subj + "'", 'already exists in cache')
        return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

    # Get word
    resp = brickdb.query('syllables', subj, fulldocs=True)

    # Invalid Response
    if resp['code'] != code['success']:
        return cached(code=code['failed'])

    # No Result - Create
    if not len(resp['result']):

        # Post Doc
        doc = { 'subject' : subj.lower(), 'syllables' : syll }
        resp = brickdb.post_docs(doc)

        # Failure
        if resp['code'] != code['success']:
            log("Unable to store syllables!")
            return cached(code=code['failed'])

        # Success
        setundo(user=bag['user_id'], 
                docs=doc,
                delete=True,
                update=resp['result'],
                response="Okay $who, forgot syllables for " + sq(subj) + '.',
                command='cache_syllables')
        log('Added new word:', subj, '-', syll, 'syllables')
    # Update word
    else:

        # Modify existing word
        doc = resp['result'][0]
        undo_doc = {   'cmd'  : 'syllables', 
                       'subj' :  doc['subject'],
                       'syll' :  doc['syllables']}
        doc['syllables'] = syll

        # Post updated document
        brickdb.update_docs(doc, undo=False)

        # Failure
        if resp['code'] != code['success']:
            log("Syllable update failed!")
            return cached(code=code['failed'])

        # Success
        setundo(user=bag['user_id'], 
                docs=undo_doc,
                update=resp['result'],
                response="Okay $who, syllables reverted.",
                command='cache_syllables')
        log("'" + subj + "'", 'updated')


    update_syllables()

    log('Learned that', "'" + subj + "'", 'has', str(syll), 'syllables')
    return { 'code' : code['success'], 'response' : "Okay, $who" }

# Updates the database with cached user data
def update_user(userid, name=None):
    global users

    # Update cache
    users[userid]['last'] = time.time()
    if name:
        users[userid]['name'] = name

    # Generate doc
    doc = users[userid].copy()
    doc['subject'] = doc['name']
    doc['subject_lc'] = doc['name'].lower()
    doc.pop('name', None)

    # Update
    log("Updating User " + sq(name) + "...")
    if '_id' in users[userid].keys():
        resp = brickdb.update_docs(doc, undo=False)

    # New
    else:
        resp = brickdb.post_docs(doc)

    result = resp['result'][0]

    # Failure
    if resp['code'] != code['success'] or result['code'] != code['success']:
        log("User update failed!")
        update_users()
        return update_user(userid, name)

    # Success
    users[userid]['_rev'] = resp['result'][0]['rev']
    return resp


# Increment a user role
def promote(mode, index, bag):

    # Get user
    doc = getlast(index)

    # Failed
    if doc['code'] != code['success']:
        return doc

    # Invalid Target
    if doc['source'] != source['userlist']:
        return { 'code' : code['missing'], 'response' : cached(["don't know"]) }

    # Determine role
    user_id = doc['id']
    old = users[user_id]['role']
    new = roles.index(old) + mode

    # Lower Limit
    if new < 0:
        log("User '" + users[user_id]['name'] + "' (" + old + ") cannot be demoted any further.")
        return { 'code' : code['denied'], 'response' : "Sorry, $who, I can't do that." }

    # Upper Limit
    if new >= len(roles):
        log("User '" + users[user_id]['name'] + "' (" + old + ") cannot be promoted any further.")
        return { 'code' : code['denied'], 'response' : "Sorry, $who, I can't do that." }

    # Change role
    resp = change_role(user_id, roles[new], bag)
    return resp


# Set user role
def change_role(user, role, bag):

    # Check if user exists
    if user not in users.keys():
        log('User not found')
        return cached(code=code['missing'])

    # Check for valid role
    if role not in roles:
        log('Invalid role specified')
        return cached(code=code['missing'])

    # Check Permission
    if user == bag['user_id'] or roles.index(bag['role']) <= roles.index(role):
        log("Permission Denied")
        return cached("[permission denied]", code=code['denied'])

    # Change role
    resp = brickdb.update_docs({ '_id' : users[user]['_id'], 'role' : role })
    if resp['code'] == code['success']:
        log("User " + sq(users[user]['name']) + " updated")

        # Update users
        update_users()
        return { 'code' : code['success'], 'response' : "Okay, $who" }

    # Failed
    else:
        log('User update failed!')
        return cached(code=code['failed'])


# Forget a user - Admin only
def remuser(userid, bag):

    # Check permission
    auth = restricted('admin', bag['role'])
    if auth['code'] != code['success']:
        return auth

    # Remove user
    docid = users[userid]['_id']
    resp = brickdb.delete_docs(docid)
    
    # Failure
    if resp['code'] != code['success']:
        return resp

    # Success
    setundo(user=bag['user_id'], 
            docs=resp['old'],
            delete=False,
            response="Okay $who, user " + sq(resp['old'][0]['subject']) + " unforgot.",
            command='cache_users')
    update_users()
    return { 'code' : code['success'], 'response' : "Okay, $who, forgot user '" + resp['old'][0]['subject'] + "'" }


# Determine self-edit
def selfcheck(subj, name):
    if re.match(re.escape(name) + '(?:\s+quote)?$', subj, re.I):
        log(name + ' is attempting to edit his own factoid!')
        return { 'code' : code['denied'], 'response' : "Please don't edit your own factoids, " + name + '.' }

    return { 'code' : code['success'] }


# Check if owner
def owner(doc, userid):

    if doc['added_by'] == userid:
        return True

    return False

# Process a delete command
# Skips authentications if bag not provided
def remfact(docid, bag=None):

    # Get Doc
    doc = brickdb.fetch(docid)
    if doc['code'] != code['success']:
        return doc

    doc = doc['result']

    # Protections
    if bag:

        # Self-editing protection
        self = selfcheck(doc['subject'], bag['name'])
        if self['code'] != code['success']:
            auth = restricted('admin', bag['role'])
            if auth['code'] != code['success']:
                resp = random.choice([cached("[permission denied]"), { 'response' : "You can't take away my memories!" }])
                resp['code'] = self['code']
                return resp

        # Check permissions - admin, op, or owner
        auth = restricted('op', bag['role'])
        if auth['code'] != code['success'] and not owner(doc, bag['user_id']):
            resp = random.choice([cached("[permission denied]"), { 'response' : "You can't take away my memories!" }])
            resp['code'] = auth['code']
            return resp

    # Delete Factoid
    old = doc.copy()
    resp = brickdb.delete_docs(doc)

    # Failed
    if resp['code'] != code['success']:
        return { 'code' : resp['code'], 'response' : "Sorry, $who, I am unable to forget that right now." }

    # Success
    setundo(user=bag['user_id'], 
            docs=old,
            delete=False,
            response="Okay $who, factoid unforgot.")
    log("Forgot '" + old['subject'] + "' " + old['mode'] + "' " + old['factoid'])
            
    # Freeze Variable Names
    resp_text = old['factoid']
    resp_text = re.sub('\$(\S+)', '[\g<1>]', resp_text)

    # Return result
    return { 'code' : code['success'], 'response' : "Okay, $who, forgot '" + old['subject'] + "' " + old['mode'] + " '" + resp_text }


# Sets or removes protection for a var
def protect_var(mode, var, bag):

    # Check permission
    auth = restricted('op', bag['role'])
    if auth['code'] == code['denied']:
        log(repr('cache'), 'command from', bag['name'], '(' + bag['role'] + ')', 'ignored')
        return auth

    # Get Var List
    resp = get_vars(var, fulldocs=True)

    # Generate list of docs to be updated
    update = []
    for row in resp['result']:
        if row['protected'] != mode:
            update.append(row)

    # No Updates
    if len(update) == 0:
        if mode:
            return { 'code' : code['conflict'], 'response' : "$who, that var is already protected." }
        else:
            return { 'code' : code['conflict'], 'response' : "$who, that var is not protected." }

    # Update docs
    old = update.copy()
    resp = tag_docs(update, protected=mode)
    if resp['code'] != code['success']:
            return resp

    # Save undo record
    if mode:
        response = "Okay $who, no longer protecting var " + sq(var) + '.'
    else:
        response = "Okay, $who, protecting var " + sq(var) + '.'
    setundo(user=bag['user_id'], 
            docs=old,
            update=resp['result'],
            response=response,
            command='cache_vars')

    # Update Cache
    update_vars()

    # Post Results
    log(len(update), 'vars updated')
    if mode:
        return { 'code' : code['success'], 'response' : "Okay, $who, protecting var " + sq(var) + "." }
    else:
        return { 'code' : code['success'], 'response' : "Okay, $who, no longer protecting var " + sq(var) + '.' }



# Tag factoids
def tag_facts(key, bag, cache_mode=None, protect_mode=None):

    # Check permission
    auth = restricted('op', bag['role'])
    if auth['code'] == code['denied']:
        log(repr('cache'), 'command from', bag['name'], '(' + bag['role'] + ')', 'ignored')
        return auth

    # Get factoids
    resp = fact_query(key, alias=False)

    # No factoids
    if not len(resp['result']):
        log("No factoids found!")
        return { 'code' : code['missing'], 'response' : cached(["don't know"]) }

    # Generate list of factoids to be updated
    update = []
    for row in resp['result']:
        if cache_mode is not None and row['cached'] != cache_mode:
            update.append(row)
        elif protect_mode is not None and row['protected'] != protect_mode:
            update.append(row)

    # No updates
    if len(update) == 0:
        if cache_mode:
            return { 'code' : code['conflict'], 'response' : "$who, '" + key + "' is already cached." }
        elif protect_mode:
            return { 'code' : code['conflict'], 'response' : "$who, '" + key + "' is already protected." }
        elif cache_mode == 0:
            return { 'code' : code['conflict'], 'response' : "$who, '" + key + "' is not cached." }
        else:
            return { 'code' : code['conflict'], 'response' : "$who, '" + key + "' is not protected." }

    # Save old values
    old_cached = update[0]['cached']
    old_protect = update[0]['protected']

    # Update factoids
    old = update.copy()
    resp = tag_docs(update, protected=protect_mode, cached=cache_mode)
    if resp['code'] != code['success']:
            return resp

    # Save undo record
    setundo(user=bag['user_id'], 
            docs=old,
            update=resp['result'],
            response=" Okay $who, factoids reverted.",
            command='cache_facts')

    # Update Cache
    update_cache()

    # Post Results
    log(len(update), 'factoids updated')
    return { 'code' : code['success'], 'response' : "Okay, $who" }


# Set the trace record
def settrace(trace):
    global state

    state['trace'] = trace

    return


# Set the undo record
def setundo(user=None, docs=None, update=None, role='op', delete=None, response=None, command=None):
    global state

    # Clear undo
    if not user or not docs:
        state['undo'] = None
        return

    # Default Response
    if not response:
        response = "Okay, $who. Undone."

    # Make List
    if type(docs) is not list:
        docs = [docs]

    # Check updates
    if update:

        # Update length differs
        if len(update) != len(docs):
            log("Warning - Update lenth doesn't match doc length!")

        # Update docs
        for x, y in zip(docs, update):

            # ID
            if 'id' in y.keys():
                x['_id'] = y['id']

            # Rev
            if 'rev' in y.keys():
                x['_rev'] = y['rev']

    # Deletions
    for x in docs:

        # Delete Docs
        if delete:
            x['_deleted'] = True

        # Restore Docs
        if delete is False:
            if '_rev' in x.keys():
                del x['_rev']
            if '_id' in x.keys():
                del x['_id']

    # Make Record
    cmd = {
        'user'     : user,
        'docs'     : docs,
        'role'     : role,
        'response' : response,
        'command'  : command
        }

    # Debugging
    if config['debug']:
        util.debug('Setting Undo Record:', cmd)

    state['undo'] = cmd

# Updates a list of full docs to be cached
def tag_docs(docs, protected=None, cached=None):

    # Modify Docs
    for doc in docs:
        if cached is not None:
            doc['cached'] = cached
        if protected is not None:
            doc['protected'] = protected

    # Update Docs
    resp = brickdb.update_docs(docs, undo=False)

    # Failure
    if resp['code'] != code['success']:
        log("Doc caching failed!")

    return resp


# Returns the doc associated with the previous post
# index is 'last' or a key associated with a list of items
def getlast(index=-1, fulldoc=False):

    # Debugging
    if config['debug']:
        util.debug('Trace:', state['trace'])

    # Invalid Index
    if type(index) is not int:
        log("Invalid index")
        return cached(code=code['failed'])

    # Invalid Trace
    if state['trace'] is None or state['trace']['source'] not in source.values():
        log('No valid target')
        return cached(code=code['missing'])

    # Internal Response
    if state['trace']['source'] == source['internal']:
        resp = state['trace']
        resp['code'] = code['success']
        return resp

    # 'that'
    if index == -1:
        if state['trace']['source'] == source['list'] and len(state['trace']['id']) > 1:
                log('Ambiguous target for command')
                return cached(code=code['failed'])
        else:
            index = 0

    # Index without list
    if index > 0 and type(state['trace']['id']) is not list:
        log("No valid target for command")
        return cached(code=code['missing'])

    # Index out of range
    if type(state['trace']['id']) is list:
        if len(state['trace']['id']) - 1 < index or index < 0:
            log("No valid target for command")
            return cached(code=code['missing'])
        else:
            doc_id = state['trace']['id'][index]
        
    # Single Entry
    else:
        doc_id = state['trace']['id']

    # Assemble response
    trace = state['trace']
    trace['id'] = doc_id
    resp = trace

    # Return Full Doc
    if fulldoc:
        doc = brickdb.fetch(doc_id)
        if doc['code'] != code['success']:
            return doc
        resp['doc']  = doc['result']
        resp['code'] = code['success']
        return resp

    # Return Doc ID
    resp['code'] = code['success']
    return resp


# Makes a new fact document
def makefact(subj, mode, fact, userid, protected=0, cached=0):

    payload = {
        'subject'   : subj,
        'subject_lc': util.depunctuate(subj),
        'factoid'   : fact,
        'protected' : protected,
        'cached'    : cached,
        'mode'      : mode,
        'added_by'  : userid,
        'added'     : time.time()
    }

    return payload


# Makes a new var document
def makevar(var, value, userid, protected=0):

    # Make document
    payload = {
        'var'   : util.depunctuate(var),
        'value' : value,
        'protected' : protected,
        'added_by'  : userid,
        'added'     : time.time()
    }

    return payload


def new_fact(subj, mode, fact, bag):
    
    # Forbidden Factoids
    if subj in forbidden:
        log("Factoid Forbidden")
        return cached("[permission denied]", code=code['denied'])

    # Self-editing protection
    self = selfcheck(subj, bag['name'])
    auth = restricted('admin', bag['role'])
    if self['code'] != code['success'] and auth['code'] != code['success']:
        return auth

    # Determine if fact exists
    resp = fact_query(subj)

    # Found
    protected = 0
    iscached = 0
    if resp['code'] != code['missing']:

        # Failed
        if resp['code'] != code['success']:
            return resp

        facts = resp['result']
        for x in facts:

            # Duplicate
            if x['factoid'] == fact and x['mode'] == mode:
                return { 'code' : code['conflict'], 'response' : "I already had it that way, $who" }

            # Protected
            if x['protected']:
                protected = 1

            # Cached
            if x['cached']:
                iscached = 1

        # Factoid protection
        auth = restricted('op', bag['role'])
        if protected and auth['code'] != code['success']:
            log("Factoid Protected")
            return auth

    # Compile Doc
    payload = makefact(subj, mode, fact, bag['user_id'], protected, iscached)
    
    # Post doc
    resp = brickdb.post_docs(payload)
    if resp['code'] != code['success']:
        return resp

    # Update Cache
    if iscached:
        update_cache()

    # Set Undo
    setundo (user=bag['user_id'], 
            docs=payload,
            update=resp['result'],
            delete=True,
            response="Okay $who, forgot " + sq(subj) + ' ' + mode + ' ' + sq(fact) + '.')
    log('Learned', repr(subj), mode, repr(fact), 'from', bag['name'])

    # Make Last
    last = {'source' : source['database'], 'id' : resp['result'][0]['id'] }
    
    # Return Response
    return { 'code' : code['success'], 'response' : 'Okay, $who', 'last' : last }


# Returns vars from the database
def get_vars(var=None, fulldocs=False):

    # Query Database
    resp = brickdb.query('vars', var, fulldocs)

    # Invalid Response
    if resp['code'] != code['success']:
        return cached(code=code['failed'])

    # No Result
    if not len(resp['result']):
        return cached(code=code['missing'])

    # Return vars
    return { 'code' : code['success'], 'response' : "Okay, $who", 'result' : resp['result'] }


# Return facts for a given subject - follows aliases
def fact_query(txt, alias=True, properties=False):

    # Query Database
    resp = brickdb.query('subjects', txt, fulldocs=True)

    # Invalid Response
    if resp['code'] != code['success']:
        return cached(code=code['failed'])

    # No Result
    if not len(resp['result']):
        return cached(code=code['missing'])
    
    # Follow Alias links
    if alias:
        result = []
        for doc in resp['result']:

            # Recursive Query
            if doc['mode'] == '<alias>':
                log('<alias>', "'" + txt + "'", '=>', "'" + doc['factoid'] + "'")
                sub_facts = fact_query(doc['factoid'])
                if sub_facts['code'] != code['success']:
                    return sub_facts
                result += sub_facts['result']

            # Compile result
            else:
                result.append(doc)

    # Un-Aliased
    else:
        result = resp['result']

    response = { 'code' : code['success'], 'response' : "Okay, $who", 'result' : result }

    # Get Properties
    if properties:
        prop = common(response['result'])
        if prop['code'] != code['success']:
            return prop
        response['properties'] = prop['result']
    
    return response

# Returns facts for a given subject and a key phrase
def query(subj, key):

    # Get facts
    resp = fact_query(subj)

    # Failure
    if resp['code'] != code['success']:
        return resp

    # Success
    facts = resp['result']

    # Filter
    result = []
    for fact in facts:
        if re.search(key, fact['factoid'], re.I):
            result.append(fact)

    if not len(result):
        return cached(code=code['missing'])

    return { 'code' : code['success'], 'result' : result }

# Return facts for a given subject and verb - follows aliases
# [ { subj, fact, mode, id, by }, ... ]
def verb_query(subj, verb, start=None):

    # Get facts
    resp = fact_query(subj)

    # Failure
    if resp['code'] != code['success']:
        return resp

    # Success
    facts = resp['result']

    # Filter
    mode = '<' + verb + '>'
    result = []
    for fact in facts:
        if fact['mode'] == mode and (start is None or re.match(re.escape(start), fact['fact'], re.I)):
            result.append(fact)
        
    return { 'code' : code['success'], 'result' : result }

# Searches for facts by field
def lookup(field, value, makelist=False):

    # Send Request
    resp = brickdb.search('factoids', field, value)

    # Invalid Response
    if resp['code'] != code['success']:
        return cached(code=code['failed'])

    # Process Result
    result = [x for x in resp['result'] if x['mode'] != '<alias>']

    # No Result
    if not len(result):
        return cached(code=code['missing'])

    return { 'code' : code['success'], 'response' : "Okay, $who", 'result' : result }


# Makes a formatted and paged list from a list of dicts
# Returns page (String), all pages (List), last (dict)
def makelist(docs, field1, field2=None, field3=None, ids=None, sort=True):

    # Make Lists
    items = []
    if field2:
        val1 = []
    else:
        val1 = None
    if field3:
        val2 = []
    else:
        val2 = None

    last = { 'source' : source['list'], 'id' : [] }

    # Sort
    if sort:
        docs = sorted(docs, key=lambda k: k[field1])

    # Fill Lists
    for x in docs:
        items.append(x[field1])
        if val1 is not None:
            val1.append(x[field2])
        if val2 is not None:
            val2.append(x[field3])
        if ids:
            last['id'].append(x[ids])

    # Collapse columns
    if val2 and not val1:
        val1 = val2
        val2 = None

    # Make rows
    rows = util.table(items, val1, val2)

    # Make pages
    (pages, bookmark) = page(rows, config['list_limit'])

    # Make Trace
    last['pages']    = pages
    last['bookmark'] = bookmark

    # Return list
    return { 'list' : pages[0], 'pages' : pages, 'last' : last}
    


# Join a list of rows into string pages
# Divides at max size
def page(rows, size=None):

    # Make pages
    if size and len(rows) > size:
        pages=[]
        for x in range(0, len(rows), size):
            excess = len(rows) - size - x
            page = rows[x:x + size]
            if excess > 0:
                page.append('and ' + str(excess) + ' more...')
            pages.append(('\n').join(page))
    else:
        pages = [('\n').join(rows)]


    # Create bookmark
    bookmark = 0

    return pages, bookmark



# Updates user cache
# Terminates on failed query
def update_users():
    global users

    # Query database
    resp = brickdb.query('users', key=bot.groupid, fulldocs=True)

    # Handle invalid response
    if resp['code'] != code['success']:
        log("Database query failed -" + str(resp))
        log("Unable to update users")
        return resp

    # Process Result
    users = {}
    for row in resp['result']:

        users[row['user_id']] = row

        # Duplicate entries for legacy support
        name = users[row['user_id']]['subject']
        users[row['user_id']]['name'] = name

    updated = len(users.keys())

    if updated:
        log("Cached data for " + str(updated) + " users")
        return { 'code' : code['success'] }

    log("Warning: No users found")
    return { 'code' : code['missing'] }        


# Constructs a response from a factoid components
def compile_fact(mode=None, subject=None, factoid=None, _id=None, **doc):

    # Verify input
    if not ( mode and subject and factoid ):
        log('Error - invalid parameters received by compile_fact!')
        return

    # Reply
    if mode == '<reply>':
        response = factoid

    # Relationship
    else:
        response = subject + ' ' + mode[1:-1] + ' ' + factoid

    # Last
    if _id:
        last = { 'source' : source['database'], 'id' : _id }
    else:
        last = { 'source' : source['internal'], 'response' : response }

    return { 'code' : code['success'], 'response' : response, 'last' : last}


# Fills variables and sends string post
# 'last' will set the trace value
def say(response=None, bag=None, last=None, trace=True, **params ):

    # No message
    if not response:
        return

    # Default trace
    if last is None:
        last = { 'source' : source['internal'], 'response' : response }
    elif 'source' not in last.keys():
        last['source'] = source['internal']

    # fill variables
    last['var'] = []
    last['val'] = []
    if bag:

        # Self
        if re.match(re.escape(bot.name) + '\s+is\s+', response, re.I):
            response = re.sub('^' + bot.name + '\s+is\s+', 'I am ', response, 1, re.I)
            last['var'].append(bot.name + ' is')
            last['val'].append('I am')

        # $who
        (response, newvars, newvals) = fill('who', bag['name'], response)
        last['var'] += newvars
        last['val'] += newvals

        # Someone
        response = re.sub('\$somebody', '$someone', response, re.I)
        (response, newvars, newvals) = fill('someone', [users[x]['name'] for x in users.keys()], response)
        last['var'] += newvars
        last['val'] += newvals

        # Fill $to with target if provided
        # Fills with random user otherwise
        if bag['to'] is None or bag['to'].lower() == bot.name.lower():
            to = ['Somebody']
            for user in users:
                if users[user]['name'].lower() != bag['name'].lower():
                    to.append(users[user]['name'])
        else:
            to = bag['to']
        (response, newvars, newvals) = fill('to', to, response)
        last['var'] += newvars
        last['val'] += newvals

        # fill other variables
        var_list = re.findall('\$(\w+)', response)
        for var in var_list:
            var = var.lower()
            if var in var_cache.keys():
                (response, newvars, newvals) = fill( var, getvalues(var), response)
                last['var'] += newvars
                last['val'] += newvals

    # Set Trace
    if trace:
        settrace(last)

    # Post Message
    return response


# Sets the case of a string to match the case of another
def setcase(txt, src):

    # Title Case
    if src.istitle():
        return txt.title()

    # Upper Case
    elif src.isupper():
        return txt.upper()

    # Lower Case
    elif src.islower():
        return txt.lower()

    # Non-cased
    else:
        return txt


# Reply with a cached factoid
def cached(subj="[don't know]", code=None):
    subj = subj.lower()

    # Check for response
    if subj in cache.keys():
        if len(cache[subj]) > 0:

            # Post response
            log('Fetching cached response')
            resp = random.choice(cache[subj])
            last = {'source' : source['cached'], 'id' : resp['id'] }
            resp = {'last' : last, 'response' : resp['value'] }
            if code:
                resp['code'] = code
            return resp

    # Attempt [don't know]
    if subj != "[don't know]":
        log('Invalid cached response request: ' + repr(subj))
        return cached(code=code)

    # Default reply
    txt = "I don't know."
    last = {'source' : source['internal'], 'response' : txt }
    resp = { 'response' : txt, 'last' : last }
    if code:
        resp['code'] = code
    return resp


# Loads configuration keys
def initialize():
    global bot

    # Load Configuration
    settings.load_config()

    # Check settings
    if config['devmode']:
        log('Developer mode enabled')
    elif config['groupme_token'] is None:
        sys.exit("No Groupme Access Token Specified - Set config var 'groupme_token'")
    if config['botname'] is None:
        sys.exit("No Groupme Bot Name Specified - Set config var 'botname'")
    if config['db_name'] is None:
        log('No database name provided.  Using botname instead.')
        config['db_name'] = config['botname']
    if config['db_key'] is None:
        sys.exit("Database API key not specified - Set config var 'db_key'")
    if config['db_pass'] is None:
        sys.exit("Database API password not specified - Set config var 'db_pass'")
    if config['db_user'] is None:
        sys.exit("Database username not specified - Set config var 'db_user'")

    # Get Bot Info
    bot = groupme.bot(config['groupme_token'], config['botname'], http, config['baseurl'])

    # Initialize Database
    resp = brickdb.initialize(http)
    if resp['code'] == code['success']:
        config['db_url'] = resp['url']

    # Load Cache
    if config['caching']:
        update_cache()

    # Load User Data
    update_users()

    # Load Syllable Cache
    update_syllables()

    # Load Vars
    if config['caching']:
        update_vars()

    # Connect Twitter
    init_twitter()

    # Plugins
    settings.load_mods(mods)

    # Load State
    loadState()

    if config['debug']:
        jprint(state)
        jprint(config)

# Fetches or generates previous state
def loadState():
    global state
    global config

    # Fetch State
    resp = brickdb.query('states', fulldocs=True)

    # Handle invalid response
    if resp['code'] != code['success']:
        log("Database query failed -" + str(resp))
        log("Unable to load state")
        return { 'code' : code['failed'] }

    # Select State
    states = resp['result']
    s = selectState(states)

    # New State
    if not s:
        s = newState()
        updateState(newstate=s)

    state = s
    if 'config' in state.keys():
        config = s['config']
    log("State loaded.")

    # Debug
    if config['debug']:
        util.debug('state ID: ' + state['_id'])
        util.debug('state Rev: ' + state['_rev'])

    return


# Chooses most recent state from a list of states
def selectState(s):

    # Eliminate invalid modes
    # Valid modes contain a config file with matching 'offline' and 'botname' settings
    s = [x for x in s if 'config' in x.keys() and x['config']['offline'] == config['offline'] and x['config']['botname'] == config['botname']]

    # Eliminate invalid versions
    old = [x['_id'] for x in s]
    s = [x for x in s if x['version'] == version]

    # Select most recent state
    if len(s):
        s = max(s, key=lambda x:x['state'])
        old.remove(s['_id'])
    else:
        s = None

    # Remove Old States
    if len(old):
        for x in old:
            brickdb.delete_docs(x)
        log(len(old), "old states removed.")
    
    return s


# Generates a new state
def newState():

    log('Generating new state...')

    state = {
        'config'       : config,
        'version'      : version,
        'uptime'       : time.time(),
        'undo'         : {},
        'history'      : [],
        'outburst'     : None,
        'trace'        : None,
        'timeout'      : 0,
        'reminder'       : {
            'day'      : 23,
            'cooldown' : 48,
            'reset'    : 0,
            'post'     : '[JC Day]'
        }
    }

    return state
    

# Updates existing state
def updateState(newstate=None):
    global state

    # New State
    if newstate is not None:
        state = newstate

    payload = state
    payload['config']  = config
    payload['version'] = version
    payload['state']   = time.time()

    # Post state
    resp = brickdb.post_docs(payload)
    if resp['code'] == code['success']:
        state['_id'] = resp['result'][0]['id']
        state['_rev'] = resp['result'][0]['rev']
        log("State updated.")
    else:
        log("State update failed!")

    return 

# Update vars from database
def update_vars(varid=None, val=None, var=None, protected=0):
    global var_cache

    # Update with provided value
    if varid and val and var:
        newvar = {'id':varid, 'val':val, 'protected' : protected}
        if var in var_cache.keys():
            var_cache[var].append(newvar)
        else:
            var_cache[var] = [newvar]
        log('var cache updated.')
        return { 'code' : code['success'] }

    # Get vars
    log('Updating cache...')
    resp = get_vars(fulldocs=True)

    # Clear cache
    var_cache = {}
    
    # Cache vars
    resp = resp['result']
    for row in resp:
        if row['var'] in var_cache.keys():
            var_cache[row['var']].append({'val':row['value'], 'id':row['_id'], 'protected':row['protected']})
        else:
            var_cache[row['var']] = [{'val':row['value'], 'id':row['_id'], 'protected':row['protected']}]

    log(len(resp), 'values cached for', len(var_cache.keys()), 'vars')
    return { 'code' : code['success'] }


# Update Syllable Cache from database
def update_syllables():

    # Clear cache
    syllables.syllcache = {}

    # Get syllables
    resp = brickdb.query('syllables')

    # Failure
    if resp['code'] != code['success']:
        log('Syllable update failed!')
        return resp

    resp = resp['result']
    
    # Cache syllables
    for row in resp:
        syllables.syllcache[row['key']] = row['value']

    log('syllable cache updated with', len(resp), 'words')
    return { 'code' : code['success'] }


# Clears and reloads the factoid cache
def update_cache():
    global cache

    # Clear cache
    cache = {}

    # Get factoids
    resp = brickdb.query('cached')

    # Failure
    if resp['code'] != code['success']:
        log('Factoid caching failed!')
        return resp

    resp = resp['result']
    
    # Cache factoids
    for row in resp:
        if row['key'] in cache.keys():
            cache[row['key']].append({ 'id' : row['id'], 'value' : row['value'] })
        else:
            cache[row['key']] = [{ 'id' : row['id'], 'value' : row['value'] }]

    log(len(resp), 'factoids cached for', len(cache.keys()), 'subjects')
    return { 'code' : code['success'] }


# Loads and authenticates a twitter API object
def init_twitter():
    global t

    # Check if available
    if config['tw_consumer'] is None:
        log('No Twitter Consumer Key specified - Twitter access not available')
    elif config['tw_consumer_secret'] is None:
        log('No Twitter Consumer Key specified - Twitter access not available')
    else:
        t = twitter.Twitter(auth=twitter.OAuth('', '', config['tw_consumer'], config['tw_consumer_secret']))
        log("Connected to Twitter")
        return

    t = None
    return


# Get Tweets from a given screenname
def gettweets(target):

    # Check if available
    if t is None:
        log("Twitter not available")
        return []
    else:

        # Get Tweets
        try:
            tweets = t.statuses.user_timeline(screen_name=target)
        except twitter.TwitterHTTPError as e:
            log('Twitter HTTP Error')
            return { 'code' : code['failed'], 'result' : [] }
        log('Fetched ' + str(len(tweets)) + ' tweets')

        return { 'code' : code['success'], 'result' : tweets }


# Processes a run-time config command
def changekey(key, mode, val=None, bag=None):

    # Unrecognized command
    if mode not in ('set', 'disable', 'enable', 'reset'):
        log('Unrecognized key command')
        return { 'code' : code['failed'], 'response' : "Sorry $who, " + sq(mode) + " is not a valid command."}

    # Check Permission
    auth = restricted('op', bag['role'])
    if auth['code'] != code['success']:
        return auth

    # Missing Value
    if val is None and mode == 'set':
        log('No value provided')
        return { 'code' : code['failed'], 'response' : "Sorry, $who, please provide a value for " + sq(key)}

    # Missing Key
    if key not in config.keys():
        log('Invalid key specified')
        return { 'code' : code['missing'], 'response' : "Sorry, $who, Key: " + sq(key) + " not found."}

    # Commands
    if mode == 'enable':
        if key in mods:
            val = 100
        else:
            val = True
    elif mode == 'disable':
        if key in mods:
            val = 0
        else:
            val = False
    elif mode == 'reset':
        if key in mods:
            val = 100
        else:
            val = None

    # Set Key
    return setkey(key, val)


# Sets a config value
def setkey(key, val=None):

    # Check for key
    if key not in defaults.keys() and key not in mods:
        return cached(code=code['missing'])

    # Load default
    if val is None:
        if key in mods:
            val = 100
        else:
            val = defaults[key]['val']

    # Convert Digits
    if key in mods or defaults[key]['type'] is int:
        if type(val) is str and util.RepresentsInt(val):
            val = int(val)

    # Convert Boolean
    if key not in mods:
        if defaults[key]['type'] is bool and type(val) is str:
            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False

    # Check type
    elif not config['devmode'] and ((key in mods and type(val) is not int) or type(val) is not defaults[key]['type']):
        return cached("[permission denied]", code=code['denied'])

    # Store value
    setenv(key, val)

    log('Configuration Updated:', repr(key), " => ", repr(val))

    # Save State
    updateState()

    return { 'code' : code['success'], 'response' : "Okay $who, configuration updated." }

# Undo the last operation
def undo(bag):

    # Check for undo record
    if not state['undo']:
        log('No undo record')
        return { 'code' : code['missing'], 'response' : "Sorry, $who, I can't undo that" }

    # Get undo record
    last = state['undo']

    # Check permission
    if last['user'] != bag['user_id']:
        auth = restricted(last['role'], bag['role'])
        if auth['code'] != code['success']:
            return auth

    # Undo
    resp = brickdb.post_docs(last['docs'])

    # Failure
    if resp['code'] != code['success']:
        return resp

    # Commands
    if last['command'] == 'cache_vars':
        update_vars()
    if last['command'] == 'cache_syllables':
        update_syllables()
    if last['command'] == 'cache_users':
        update_users()
    if last['command'] == 'cache_facts':
        update_cache()

    # Success
    setundo()
    return { 'code' : code['success'], 'response' : last['response'] }


# Set an environmental variable
def setenv(key, val=None):
    config[key] = val


# Load Configuration
initialize()