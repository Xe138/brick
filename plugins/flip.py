# Flip
# Flips text
# Version 1.0.0
import re
from plugins.flip_lib import upsidedown

def main(bag, config):

    limit = 20

    match = re.match('(?:flip\s+(.+))', bag['msg'], re.I)
    if not match:
        return

    flipped = ""
    txt = match.group(1)

    if len(txt) > limit:
        return

    flipped = upsidedown.transform(txt)
    return "(╯°□°)╯︵" + flipped