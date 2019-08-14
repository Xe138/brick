# Hooyah 23
# Responds to mentions of 23
# Version 1.0.1
import re

def main(bag, config):

    max_seperation = 8

    match = re.search('((?:\s|^)(?:2|two|twenty)\D{0,' + str(max_seperation) + '}(?:3|three)(?:\s|$))', bag['msg'], re.I)
    if match:
        return 'Hooyah 23!'