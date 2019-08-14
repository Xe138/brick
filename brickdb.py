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
import json
import requests
from settings import config
from settings import code
from time import sleep
from util import *

http = None

# Check the status of the database
def initialize(interface):
    global http

    # Store http interface
    http = interface

    # Generate Database URL
    url = "https://{0}:{1}@{2}.cloudant.com/{3}".format(config['db_key'], config['db_pass'], config['db_user'], config['db_name'])

    # Test URL
    retry = True
    while (retry):
        try:
            resp = http.get(url)

            # Handle invalid response
            if resp.status_code != requests.codes.ok:
                resp.raise_for_status()
            else:
                retry = False
        except Exception as err:
            log("Unable to connect to database - " + str(err))
            log('Reattempting in 5 seconds.')
            sleep(5)

    log("Connected to database")
    return { 'code' : code['success'], 'url' : url}


# Queries a view for results
def query(dbview, key=None, fulldocs=False, limit=None, skip=None, group=None, group_level=None):

    # Generate Request
    if key:
        key = depunctuate(key)
        payload = { "keys" : [key] }
    else:
        payload = None

    # Send Request
    return view('main', dbview, fulldocs, payload, limit=limit, skip=skip, group=group, group_level=group_level)


# Performs a search for values in a given field
def search(index, field, value):

    # Send request
    url = config['db_url'] + '/_design/main/_search/' + index
    param = {   'include_docs' : json.dumps(True), 'q' : field + ':' + value }
    resp = get(url, params=param)

    # Extract Docs
    result = [x['doc'] for x in resp['result']]
    return { 'code' : code['success'], 'result' : result }


# Returns documents in a given view
def view(design, dbview, include_docs=False, payload=None, limit=None, skip=None, group=None, group_level=None):

    # Base URL
    url = config['db_url'] + '/_design/' + design + '/_view/' + dbview

    # Parameters
    params = {}
    if include_docs:
        params['include_docs'] = json.dumps(include_docs)
    if limit:
        params['limit'] = limit
    if skip:
        params['skip'] = skip
    if group:
        params['group'] = json.dumps(group)
    if group_level:
        params['group_level'] = group_level

    # Query Database
    if payload is None:
        docs = get(url, params=params)
    else:
        docs = post(url, payload=payload, params=params)

    # Query Failed
    if docs['code'] != code['success']:
        return docs

    # Extract embedded docs
    if include_docs:
        docs['result'] = extract(docs['result'])

    return docs


# Removes documents from the database
# accepts a list of ID strings or dicts
def delete_docs(docs, undo=True):

    # Convert to list
    if type(docs) is not list:
        docs = [docs]

    # Verify input
    update = []
    for x in docs:

        # Convert IDs
        if type(x) is str:
            doc = { '_id' : x }
        else:
            doc = x

        # Update docs
        doc['_deleted'] = True
        update.append(doc)

    return update_docs(update, undo=undo)


# Adds documents to the database
# Returns doc ID
def post_docs(docs):

    # Convert to List
    if type(docs) is dict:
        docs = [docs]
    elif type(docs) is not list:
        log('Parameters must be a dictionary or list of dictionaries!')
        return { 'code' : code['failed'] }

    # Build payload
    payload = { 'docs' : docs }
    url = config['db_url'] + '/_bulk_docs'

    # Post docs
    resp = post(url, payload)

    return resp



# Updates documents in the database
# Returns the old docs
def update_docs(docs, undo=True):

    # Convert to List
    if type(docs) is dict:
        docs = [docs]
    elif type(docs) is not list:
        log('Parameters must be a dictionary or list of dictionaries!')
        return { 'code' : code['failed'] }

    # Prepare Updates
    payload = []
    old = []
    for x in docs:

        # Missing ID
        if '_id' not in x.keys():
            log('Doc ID missing!')
            return { 'code' : code['failed'] }          

        # Get docs
        if undo or '_rev' not in x.keys():
            log('Fetching document ' + repr(x['_id']))
            old_doc = fetch(x['_id'])['result']
            update = merge_dict(old_doc, x)
            if undo:
                old.append(old_doc)
        else:
            update = x

        # Set payload
        payload.append(update)

    # Post Docs
    resp = post_docs(payload)

    # Return Result
    if undo:
        return { 'code' : resp['code'], 'result' : resp['result'], 'old' : old}
    else:
        return { 'code' : resp['code'], 'result' : resp['result'] }
        

# Return a document with the provided ID
# Returns in the format provided
def fetch(doc_ids):

    if type(doc_ids) != list:
        single = True
        doc_ids = [doc_ids]
    else:
        single = False

    docs = [get(config['db_url'] + '/' + x) for x in doc_ids]

    if single:
        return docs[0]
    else:
        return docs

# Performs an HTTP POST request
def post(url, payload, params=None):

    # Debugging
    if config['debug']:
        debug("Posting...", { 'url' : url, 'payload' : payload, 'params' : params })

    headers = {'content-type': 'application/json'}
    resp = http.post(url, data=json.dumps(payload), headers=headers, params=params)
    resp = parse(resp)

    # Debugging
    if config['debug']:
        debug("Response:", resp)

    return resp

# Performs an HTTP GET request
def get(url, params=None):

    # Debugging
    if config['debug']:
        debug("Getting...", { 'url' : url, 'params' : params })

    resp = http.get(url, params=params)
    resp = parse(resp)

    # Debugging
    if config['debug']:
        debug("Response:", resp)


    return resp

# Verifies successful response and returns the content
def parse(resp):

    result = resp.json()

    # Extract docs
    if type(result) is dict:
        result = result.get('rows', result)

    # Quit if request failed
    if resp.status_code not in (requests.codes.ok, requests.codes.created, requests.codes.accepted):
        log("Database query failed - " + str(resp.status_code) + ': ' + result['reason'])
        return { 'code' : code['failed'] }

    # Detect database errors
    if type(result) is list:
        for x in result:
            if type(x) is dict and 'error' in x.keys():
                log("Warning - database error! -", x['reason'])
                x['code'] = code['failed']
            else:
                x['code'] = code['success']

    # Return content
    return { 'code' : code['success'], 'result' : result }

# Extracts full docs from a view result
def extract(data):

    docs = [ x['doc'] for x in data ]

    return docs