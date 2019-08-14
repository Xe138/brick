# Trump Speech
# Generates a random Donald Trump speech
# Version 1.0.0
import re
from plugins.trumpspeech_lib import markov


def main(bag, config):
    if re.match('trump\s*speech', bag['msg'], re.I):
        resp = markov.generate('plugins/trumpspeech_lib/trumpspeech.txt', 200)
        resp = '...' + resp + '...'
        return resp
