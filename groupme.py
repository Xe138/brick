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

from time import sleep
import settings
import requests
from util import log

class bot:

    http = None

    def __init__(self, token, name, interface, baseurl='https://api.groupme.com/v3'):
        self.token = token
        self.name = name
        self.baseurl = baseurl
        self.http = interface
        self.get_botinfo()

    def post(self, msg):
        resp = self.http.post(self.baseurl + '/bots/post', data={
                'bot_id' : self.botid,
                'text'   : str(msg)
                })

        # Handle invalid response
        if resp.status_code != requests.codes.accepted:
            try:
                resp.raise_for_status()
            except Exception as err:
                log("Message post failed - " + str(err))
                return { 'code' : settings.code['failed'] }

        # Success
        log("Message Posted:", repr(msg))

    # Get Groupme info for bot
    def get_botinfo(self):
        errors = (requests.exceptions.SSLError, requests.packages.urllib3.exceptions.ProtocolError)

        # Request bot info
        url = self.baseurl + "/bots?token=" + self.token
        retry = True
        while (retry):
            try:
                resp = self.http.get(url)
                retry = False
            except errors as err:
                log("Groupme Connection Failed - " + str(err))
                log("Reattempting in 5 seconds.")
                sleep(5)

        # Handle invalid response
        if resp.status_code != requests.codes.ok:
            log("Unable to retrieve bot info.")
            resp.raise_for_status()
        
        # Load bot data
        result = resp.json()['response']
        for x in result:
            if x['name'] == self.name:
                self.groupid = x['group_id']
                self.botid = x['bot_id']
                log('Connected to Groupme as ' + repr(self.name))
                break
        else:
            sys.exit("No bots found named " + repr(self.botname))

    # Get post history
    def history(self):

        # Get messages
        url = self.baseurl + "/groups/" + self.groupid + '/messages?token=' + self.token
        resp = self.http.get(url)

        # Handle invalid response
        if resp.status_code != requests.codes.ok:
            log('Unable to retrieve groupme messages!')
            return { 'code' : settings.code['failed'] }

        # Assemble response
        posts = resp.json()['response']['messages']

        # No posts
        if not len(posts):
            log('No messages found')
            return { 'code' : settings.code['missing'] }

        # Success
        return { 'code' : settings.code['success'], 'result' : posts }