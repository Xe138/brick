# Checks for a haiku in the previous 3 posts
# Version 1.0.0
import re

def main(bag, config):

	if bag['syll'] == 5 and len(bag['history']) >= 2:

		# Extract history
		posts = bag['history']

		# Haiku Check
		if posts[-1]['syll'] == 7 and posts[-2]['syll'] == 5:
			print('Haiku found!')

			# Construct factoid
			subj = 'haiku'
			mode = '<reply>'
			fact = posts[-2]['text'] + '\n' + posts[-1]['text'] + '\n' + bag['text']

			# Return commands
			return { 
				'learn' : { 
					'subj' : subj,
					'mode'    : mode,
					'fact'    : fact
					},
				'msg' : 'Was that a Haiku?'
				}