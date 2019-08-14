# Gets a brief summary of a subject from wikipedia
# Version 1.1.0
import re
import json
import requests
import random
import nltk

baseurl = 'http://en.wikipedia.org/w/api.php'

# Return an extract of a random page
def random_page(size=10):

    payload = {
        'format'         : 'json',
        'action'         : 'query',
        'list'           : 'random',
        'rnlimit'        : size,
    }

    resp = requests.get(baseurl, params=payload)

    if resp.status_code != requests.codes.ok:
        return

    # Eliminate undesired pages
    pageid = [ x for x in resp.json()['query']['random'] if not re.search(r'\w+:\w+|\(disambiguation\)', x['title'])]

    # Select random page
    if len(pageid):
        pageid = random.choice(pageid)['id']
        return pageid


# Returns a page
def getpage(titles=None, pageid=None, sentences=1):

    # Get random page
    if titles is None and pageid is None:
        pageid = random_page()
        if pageid is None:
            return

    # Payload template
    payload = {
        'format'         : 'json',
        'action'         : 'query',
        'prop'           : 'extracts|info|categories|links',
        'explaintext'    : True,
        'exsentences'    : sentences + 1,
        'continue'       : '',
        'inprop'         : 'url',
        'clshow'         : 'hidden',
        'redirects'      : True
    }

    if titles is not None:
        payload['titles'] = titles
    else:
        payload['pageids'] = pageid

    resp = requests.get(baseurl, params=payload)

    if resp.status_code != requests.codes.ok:
        return

    resp = resp.json()['query']['pages']
    page = next(iter(resp.values()))

    return page


# Returns an extract of a page
# Random page if not specified
def extract(titles=None, pageid=None, sentences=1):

    page = getpage(titles=titles, pageid=pageid, sentences=sentences)

    # No Matches
    if page is None or 'missing' in page.keys():
        return None, None

    # Filter redirects
    if 'redirect' in page.keys():
        return None, None

    ex = page['extract']
    url = page['fullurl']

    # Remove pronunciations
    ex = re.sub(r'\s(?:\(.*)?(?:/.+/)(?:.*\))?', '', ex, re.U)

    # Trim sentences
    ex = ('  ').join(nltk.tokenize.sent_tokenize(ex)[0:sentences])

    # Follow random disambiguation
    if 'categories' in page.keys():
        if 'extract' not in page.keys() or re.search('refers? to:$',page['extract'], re.I):
            for x in page['categories']:
                if x['title'] in ('Category:All disambiguation pages', 'Category:All set index articles'):
                    (ex, url) = extract(titles=random.choice(page['links'])['title'],sentences=sentences)
                    break

    return ex, url

def main(bag, config):

    # Something Random
    if bag['addressed'] and re.match('something\s*(?:interesting|random)\s*[\.!]?$', bag['msg'], re.I):
        (ex, url) = extract()

    else:

        # Test for question
        match = re.match(r'(?:what\s+(?:is|are)|what\'s|who\'s|who\s+(?:is|are))\s+(?:(?:a|the)\s+)?(.+?)\?*$', bag['msg'], re.I)
        if match is not None:
            subj = match.group(1).title()

            # Prevent invalid characters
            if re.search('[<>]', bag['msg'], re.I):
                return

            # Get definition
            (ex, url) = extract(titles=subj)

        else:
            return
    
    if ex is None:
        return
    
    return { 'msg' : ex, 'last' : {'response' : url} }