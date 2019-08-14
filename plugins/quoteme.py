# Quote Me
# Quotes people who do not want to be quoted
# Version 1.0.0
import re

def main(bag, config):

    # Ignore Commands
    if re.search('<\w+>|=>', bag['msg']):
        return

    # Ignore URLs
    if re.search('www\.|\S+\.\S+', bag['msg'], re.I):
        return

    # Don't Quote Me
    match = re.match('don\'t quote me(?: on this)?, but (.+)', bag['msg'], re.I)
    if match == None:
        return

    msg = match.group(1)
    response = '"' + msg + '" --' + bag['name']

    # Learned Quote
    print('Learned Quote from ' + bag['name'])

    # Construct factoid
    subj = bag['name'] + ' quote'
    mode = '<reply>'
    fact = bag['name'] + ': "' + msg + '"'

    # Return commands
    return { 
        'learn' : { 
            'subj'    : subj,
            'mode'    : mode,
            'fact'    : fact
            },
        'msg' : response
        }