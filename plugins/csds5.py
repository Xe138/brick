# CSDS5
# Responds to mentions of CSDS-5 with a factoid
# Version 1.0.0
import re
import random

user = 'Greeeeeeetttttaaaaaa dawg'

response = [
	'I wonder if @' + user + ' knows anything about that.',
	'@' + user + ' might know something about that.',
	'You should ask @' + user + ' about that.',
	'@' + user + ', do you know anything about that?'
	]

def main(bag, config):

	# Ignore if posted by target user
	if bag['name'].lower() == user.lower():
		return

	# Return random response
	if re.search('CSDS-?5|(?:sub-?)?devron 5', bag['msg'], re.I):
		return random.choice(response)