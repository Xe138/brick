# Brick is a modular and expandable chat-bot capable of basic learning and information fetching by API calls.
# Copyright (C) 2015  Bill Ballou

# This file is part of Brick.

# Brick is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.

# Brick is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Brick.  If not, see <http://www.gnu.org/licenses/>.

import re
import json
import math
import calendar
import datetime
import random
import nltk

# nltk.download('cmudict')
# nltk.download('punkt')

# Prints JSON data
def jprint(data, limit = None):

    # Convert to String
    dump = json.dumps(data, indent=4, sort_keys=True)

    # Truncate
    if limit and len(dump) > limit:
        dump = dump[0:limit] + '\n(JSON truncated...)'

    # Print
    log(dump)

# Returns a value varied by a random amount
def vary(value, spread):
    value = (random.uniform(spread, 1 + spread) * value)
    return value

# Removes extra spaces, trailing punctuation, and case
def depunctuate(msg):
    new = msg.lower()
    new = new.strip()
    new = re.sub('[!\.\?,:;-]*', '', new, 0, re.I).strip()
    return new

# Constructs a time string from seconds
def string_time(time):

    # Calculate time
    m, s = divmod(time, 60)
    h, m = divmod(m, 60)

    # Build String
    time = ''
    h = int(h)
    m = int(m)
    s = int(math.floor(s))
    if h:
        time += str(h) + 'h '
    if m:
        time += str(m) + 'm '
    if s or time == '':
        time += str(s) + 's'

    return time.strip()

# Construct a date string from seconds
def string_date(s):
	return datetime.datetime.fromtimestamp(s).strftime('%Y-%m-%d %H:%M:%S')


# Merge Two Dictionaries
def merge_dict(a, b):
    c = a.copy()
    c.update(b)
    return c


# Returns the longest item in a list of items
def longest(items):
    longest = max(items, key=len)
    return longest


# Makes an indexed list of rows with justified columns
def table(items, val1=None, val2=None):

    # Accept non-list item
    if type(items) is not list:
        items = [items]

    # Fill Null values
    if val1 is None:
        val1 = [''] * len(items)
    if val2 is None:
        val2 = [''] * len(items)

    # Make Strings
    items  = [ str(x) if x is not None else '' for x in items ]
    val1 = [ str(x) if x is not None else None for x in val1 ]
    val2 = [ str(x) if x is not None else None for x in val2 ]

    # Find longest item + digit length
    pad = 1
    maxspace1 = len(longest(items)) + len(str(len(items))) + pad
    maxspace2 = len(longest(items))  + pad

    # Make index
    index = [str(x) for x in range(0,len(items))]

    # Make rows
    table = []
    for number, item, field1, field2 in zip(index, items, val1, val2):
        row = number + ') ' + item
        if field1 is not None:
            row = row + ' ' * (maxspace1 - len(item) - len(number)) + field1
        if field2 is not None:
            row = row + ' ' * (maxspace2 - len(field1)) + field2
        table.append(row)

    return table


# Add single quotes around a string
def sq(string):
    return "'" + string + "'"

# Add double quotes around a string
def dq(string):
    return '"' + string + '"'

# Prints debug message
def debug(msg='', json=None):
    log("(DEBUG)", msg)
    if json:
        jprint(json, limit=4000)

# Prints a log message
def log(*msg):

    # Attempt print
    try:
        print(*msg)

    # Encode to Bytes
    except UnicodeEncodeError:
        encoded = []
        for x in msg:

            if type(x) is str:
                x = x.encode('utf-8', 'replace')

            encoded.append(x)

        print(*encoded)


# Returns the integer day of the month with a given hour offset
def today(offset=0):
    utc = datetime.datetime.now(datetime.timezone.utc)
    local = utc.astimezone(tz=datetime.timezone(datetime.timedelta(hours=offset)))
    return local.day

# Returns a single value from a dict
def isolate(x):
    return next(iter(x.values()))


# Divides a string into strings of character maximum
# Attempts division by new lines, then sentences, then words, then characters
def divide(txt, limit):
    
    chunks = []

    # By Line
    lines = re.split('(\n)', txt)
    for line in lines:
        if len(line) <= limit:
            chunks.append(line)
        else:

            # By sentence
            sentences = re.split('(\. |! |\? )', line)
            for sentence in sentences:
                if len(sentence) <= limit:
                    chunks.append(sentence)
                else:

                    # By word
                    words = re.split('( )', sentence)
                    for word in words:
                        if len(word) <= limit:
                            chunks.append(word)
                        else:

                            # By Char
                            for char in word:
                                chunks.append(char)

    posts = ['']
    for chunk in chunks:
        if len(posts[-1]) + len(chunk) <= limit:
            posts[-1] += chunk
        else:
            # posts[-1] = posts[-1].strip()
            posts.append(chunk)
    # posts[-1] = posts[-1].strip()

    return posts


def RepresentsInt(s):
    try: 
        int(s)
        return True
    except ValueError:
        return False