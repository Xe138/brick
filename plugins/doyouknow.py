# Do you know?
# Responds to 'do you know' and 'does anyone know'
# Version 1.0.0
import re

def main(bag, config):

	if re.match('(?:Do\s+you|Does\s+anyone)\s+know\s+(\w+)', bag['msg'], re.I):
		return 'No, but if you hum a few bars I can fake it.'