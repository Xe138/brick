# Your Mom
# "Your MOM is..."
# Version 1.0.2
import re

def main(bag, config):

    match = re.match('(.+)\s+is(?:\s+also)?\s+[^\?]+$', bag['msg'], re.I|re.DOTALL)
    if match != None:
        msg = re.sub(re.escape(match.group(1)), 'Your mom', bag['msg'], 1)
        print('old:', match.group(1))
        print('new:', msg)

        return msg