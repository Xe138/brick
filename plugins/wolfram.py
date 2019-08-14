# Query Wolfram-Alpha for question answers
# Version 1.0.1
import re
import json
import urllib
import requests
import xmltodict

# Format a response as a table
def table(text):

    # Find farthest |
    lines = re.split('\n', text)
    lines = [ re.split('\|', x, 1)[0:2] if '|' in x else x for x in lines ]
    broken = [ x[0] for x in lines if type(x) is list ]
    if len(broken):
        div = len(max(broken, key=len))
    else:
        return text

    # Pad to farthest |
    lines = [ x[0] + ' ' * (div-len(x[0])) + '|' + x[1] if type(x) is list else x for x in lines ]
    text = ('\n').join(lines)

    return text


# Prints JSON data
def jprint(data):

    print(json.dumps(data, indent=4, sort_keys=True))


# Gets a plain-text answer
def answer(subj, appid):

    baseurl = 'http://api.wolframalpha.com/v2/query'

    parameters = {
        'appid'       : appid,
        'input'       : subj,
        'podindex'    : '1,2',
        'format'      : 'plaintext,image',
        'units'       : 'nonmetric',
        # 'scantimeout' : 1,
        # 'parsetimeout': 1
    }

    # Query
    resp = requests.get(baseurl, params=parameters)
    if resp.status_code != requests.codes.ok:
        return
    data = xmltodict.parse(resp.text)['queryresult']

    # Filter none-answers
    if data['@success'] == 'false' or data['@numpods'] == '0' or '@nodata' in data.keys():
        return

    # Get Sources
    if 'sources' in data.keys() and int(data['sources']['@count']):
        sources = data['sources']['source']
    else:
        sources = None

    # Get Title
    title = data['pod'][0]['subpod']['plaintext']
    title = re.sub(' \| ', ' ', title)

    # Get SubPod
    data = data['pod'][1]['subpod']
    if type(data) is list:
        data = data[0]

    # Get Answer
    text = data['plaintext']
    img = data['img']['@src']

    # Format table
    if '\n' in text:
        text = title + ':\n' + table(text)
    else:
        text = title + ': ' + text

    return {'text' : text, 'img' : img, 'sources' : sources}


def main(bag, config):

    # Test for question 
    if re.match(r'(?:what|how)(?:\'?s)?\s+.+\?$', bag['msg'], re.I):
        pass

    # Test for operators
    elif re.search(r'[\+\-/\*]', bag['msg']) and bag['addressed']:
        pass

    # Exit
    else:
        return

    # Query Server
    subj = bag['msg']
    appid = config['wolframid']
    result = answer(subj, appid)

    if result is None:
        return

    # Compile Sources
    if result['sources'] is not None:
        if type(result['sources']) is list:
            source = ('\n').join([ x['@text'] + ': ' + x['@url'] for x in result['sources']])
        else:
            x = result['sources']
            source = x['@text'] + ': ' + x['@url']
    else:
        # Generate Clickable URL
        source = 'http://www.wolframalpha.com/input/?' + urllib.parse.urlencode({'i' : bag['msg']})

    return {'msg' : result['text'], 'img' : result['img'], 'last' : {'response' : source}}