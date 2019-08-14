# Say Something
# Says something like a smartass
# Version 1.0.1
import re

def main(bag, config):

	match = re.match('say (.*)', bag['msg'], re.I|re.DOTALL)
	if match != None:
		return match.group(1) + '!'