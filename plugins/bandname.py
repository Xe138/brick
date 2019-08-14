# Band Names
# Identifies potential band names and learns them
# Version 1.1.1
import re

def main(bag, config):

    # Ignore Commands
    if re.search('<\w+>|=>', bag['msg']):
        return

    # Ignore URLs
    if re.search('www\.|\S+\.\S+', bag['msg'], re.I):
        return

    # Ignore Questions
    if re.match('.+\?', bag['msg'], re.I):
        return

    words = bag['msg'].split()

    # 3 Words
    if len(words) != 3:
        return

    # Strip Characters
    phrase = re.sub('[<>=#@]', '', bag['msg'])
    phrase = phrase.title()

    # Learn new band name
    print('Band Name Found')
    return { 'addval' : { 
        'var'     : 'band',
        'val'     : phrase, 
        'success' : '"' + phrase + '" would be a good name for a band.'
        }}