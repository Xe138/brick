# sexchange
# changes 'ex' to 'sex'
# Version 1.0.0
import re

def main(bag, config):

    match = re.search(r'\b(ex.*)\b', bag['msg'], re.I)
    if match != None and match.group(1) not in ('extra', 'except'):
        if re.search(r'\ban ex', bag['msg']):
            msg = re.sub(r'\ban ex', 'a sex', bag['msg'], 1, re.I)
        else:
            msg = re.sub(r'\bex', 'sex', bag['msg'], 1, re.I)
        return msg