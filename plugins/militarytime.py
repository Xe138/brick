# Military Time
# Converts time to military time
# Version 1.0.0
import re

def main(bag, config):
    
    match = re.search(r'\b(\d{1,2})(?:\:(\d{2}))?([ap])m\b', bag['msg'], re.I)
    if match != None:
        hour, minute, period = match.group( 1, 2, 3 )
        hour = int(hour)

        # Idiot Check
        if hour > 12 or hour < 1:
            return

        # Zero Minutes
        if minute == None:
            minute = '00'

        # Correct Time
        if (period == 'p' and hour < 12):
            hour += 12
        elif ( hour < 10 ):
            hour = '0' + str(hour)
        elif ( hour == 12 and period == 'a'):
            hour = '00'

        # Trailing Zeros
        hour = str(hour)
        time = hour + minute

        return "That's " + time + " for you military types."