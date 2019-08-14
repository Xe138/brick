# Silence
# Generates a response to posted elipses or other indicators of a silent response
# Version 1.0.0
import re

def main(bag, config):

	# 3 or more '.'
	if re.match(r'\.\.\.+$', bag['msg']):
		return { 'lookup' : '[silence]' }