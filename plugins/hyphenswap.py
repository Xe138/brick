# Hyphen Swap
# Shifts the hyphen in a phrase
# Version 1.0.0
import re

def main(bag, config):

	match = re.search('(\w+)-ass\s+(\w+)', bag['msg'], re.I)
	if match != None:
		msg = re.sub('(\w+)-ass\s+(\w+)', '\g<1> ass-\g<2>', bag['msg'], re.I)
		return msg