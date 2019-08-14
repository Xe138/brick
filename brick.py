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

# External Modules
import os
import sys
import json
import time

# Local Modules
import core
import util
from util import log
from core import config
from core import bot

# POST requests
def handler(data=None):

    # No input
    if not data:
        return

    try:

        # Process
        resp = core.process(data)
        post(resp)
    
        return

    # Handle Errors
    except Exception as err:
        if config['debug']:
            raise
        else:
            log("ERROR - " + str(err))


# Heartbeat
def heartbeat():

        resp = core.heartbeat()
        post(resp)


# Post text to Groupme
def post(posts):

    # Ignore None
    if not posts:
        return

    # Limit post characters
    if len(posts) > config['post_limit']:
        posts = util.divide(posts, config['post_limit'])

    # Convert to list
    if type(posts) is str:
        posts = [posts]
    elif type(posts) is not list:
        log('Invalid post request -', posts, type(posts))
        return

    # Offline
    if config['offline']:

        for msg in posts:
            log("Response:", msg)
        return

    # Online
    else:

        # Post Message
        for msg in posts:
            
            # Response Delay
            time.sleep(config['resp_delay'])
            resp = bot.post(msg)