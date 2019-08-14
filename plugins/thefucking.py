# The Fucking
# Re-arranges 'the fucking' to 'fucking the'
# Version 1.0.0
import re

def main(bag, config):

    msg = re.sub('the\s+fucking', 'fucking the', bag['msg'], 1, re.I)

    if msg != bag['msg']:
        return msg