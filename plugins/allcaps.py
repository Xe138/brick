# All Caps
# Generates a response if an all caps post is made
# Version 1.0.0
import re

def main(bag, config):

	if re.match('[\sA-Z]*[A-Z]{4,}\s+[\sA-Z]{4,}[\?!\.]*$', bag['msg']):
		return { 'lookup' : '[allcaps]' }