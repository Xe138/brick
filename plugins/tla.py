# Matches a 3-letter acronym with a band name
# Version 1.0.1
import re

def main(bag, config):

    # 3 Capital Letters
    if re.match('([A-Z])([A-Z])([A-Z])\??$', bag['msg']):
        return { 'call' : 'getvar', 'var' : 'band' }

def recall(bag, config, bands):

    # No bands
    if not bands:
        return

    # Extract Letters
    match = re.match('([A-Z])([A-Z])([A-Z])\??$', bag['msg'])
    pattern = match.group(1, 2, 3)
    
    # Look for match
    for band in bands:
        match = re.match('(\w)\w*\s+(\w)\w*\s+(\w)\w*', band.upper())
        if match != None:
            if pattern == match.group(1, 2, 3):
                return '$Who, "' + band + '"?'

    return