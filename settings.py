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

import sys
import os
import yaml
from util import log

config = {}
mods = []
env = {}

roles = ['user', 'op', 'admin']

forbidden = ['that']

forbidden_var = ['who', 'to', 'someone']

code = {
    'failed'    : '0',
    'success'   : '1',
    'denied'    : '3',
    'missing'   : '4',
    'conflict'  : '5'
}

source = {
    'internal'  : '0',
    'cached'    : '1',
    'database'  : '2',
    'list'      : '3',
    'varlist'   : '4',
    'userlist'  : '5'
}

defaults = {
    'timezone'     : {
        'val'      : -5,
        'type'     : int,
        'hidden'   : False
        },
    'debug'        : {
        'val'      : False,
        'type'     : bool,
        'hidden'   : False
        },
    'caching'      : {
        'val'      : True,
        'type'     : bool,
        'hidden'   : False
        },
    'baseurl'      : {
        'val'      : 'https://api.groupme.com/v3',
        'type'     : str,
        'hidden'   : True
        },
    'devmode'      : {
        'val'      : False,
        'type'     : bool,
        'hidden'   : False
        },
    'groupme_token': {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'heroku_token' : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'botname'      : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'db_key'       : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'db_name'      : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'db_pass'      : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'db_user'      : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'db_url'       : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'tw_consumer'  : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'tw_consumer_secret' : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'min_length'   : {
        'val'      : 6,
        'type'     : int,
        'hidden'   : False
        },
    'max_length'   : {
        'val'      : 150,
        'type'     : int,
        'hidden'   : False
        },
    'offline'      : {
        'val'      : False,
        'type'     : bool,
        'hidden'   : True
        },
    'mutetime'     : {
        'val'      : 60,
        'type'     : int,
        'hidden'   : True
        },
    'post_limit'   : {
        'val'      : 400,
        'type'     : int,
        'hidden'   : False
        },
    'list_limit'   : {
        'val'      : 20,
        'type'     : int,
        'hidden'   : False
        },
    'post_history' : {
        'val'      : 3,
        'type'     : int,
        'hidden'   : False
        },
    'wolframid'    : {
        'val'      : None,
        'type'     : str,
        'hidden'   : True
        },
    'resp_delay'   : {
        'val'      : 5,
        'type'     : int,
        'hidden'   : False
        },
    'outburst'     :{
        'val'      : 24,
        'type'     : int,
        'hidden'   : False
    }
}

def load_config():
    global config

    # Load environment
    loadenv()

    # Load Keys from environment settings and defaults
    for key in defaults.keys():
        val = defaults[key]['val']
        typ = defaults[key]['type']
        if type(val) is not typ and val is not None:
            sys.exit("Default Configuration Corrupted. Key '" + key + "' set to " + repr(val) + " (" + str(type(val)) + " - " + str(typ) + " expected)")
        config[key] = load(key)
    log('Configuration Loaded')

# Locates and returns config value
def load(key):

    # If configuration value found in config, return it
    val = getenv(key)
    if val is not None:

        # Current Setting
        if key in config.keys():
            old = config[key]
        elif key in mods:
            old = 100
        else:
            old = defaults[key]['val']

        # Set data type
        if key in mods:
            def_type = int
        else:
            def_type = defaults[key].get('type', int)
        val = convert(val, def_type)

        # Check type
        if type(val) is not def_type:
            log('Invalid type for key "' + key + '" - Loading default.')
            return old

        return val

    # If configuration found in defaults, return it
    if key in defaults:
        return defaults[key]['val']

    # Returns None is value not found
    return None


# Converts data to required type
def convert(val, val_type):

    # No conversion
    if type(val) is val_type:
        return val

    # to str
    if val_type is str:
        return str(val)

    # to int
    if val_type is int:
        return int(val)

    # to bool
    if val_type is bool:

        # normalize str
        if type(val) is str:
            val = val.lower()

        # Convert
        if val in ['true', 'yes', 1]:
            return True
        elif val in ['false', 'no', 0]:
            return False

    return val



# Loads the environmental variables from a YML file
def loadenv(file='env.yml'):
    global env

    # Check Env file
    try:
        with open("env.yml", 'r') as stream:
            env = yaml.load(stream)
    except IOError:
        env = {}


# Gets a value from an environmental variable
def getenv(key):

    # Check env file
    if key in env.keys():
        return env[key]

    # Check environment
    val = os.getenv(key)

    return val


# Initialize mods given in a list
def load_mods(mod_list):
    global mods

    mods = mod_list
    for mod in mods:
        config[mod] = load(mod)
        if config[mod] is None:
            config[mod] = 100
    log(str(len(mods)) + " Plugin(s) Loaded")