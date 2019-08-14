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
from nltk.corpus import cmudict

# Initialize nltk - cmudict
# import nltk
# nltk.download()

# Dictionary
d = cmudict.dict()

# Syllable cache
syllcache = {}

# Returns the number of syllables in a string
def find(msg):

    # Strip Case
    msg = msg.lower()

    # Add Space to CamelCased words
    msg = re.sub(r'([a-z])([A-Z])', '\g<1> \g<2>', msg)

    # Seperate Numbers
    msg = re.sub(r'([a-zA-Z])(\d)', '\g<1> \g<2>', msg)
    msg = re.sub(r'(\d)([a-zA-Z])', '\g<1> \g<2>', msg)

    # Dates
    msg = re.sub(r'\b(1[89]|20)(\d\d)\b', '\g<1> \g<2>', msg)

    # Comma-form numbers
    msg = re.sub(r',(\d\d\d)', '\g<1>', msg)

    # Greater/Less Than
    msg = re.sub(r'([a-zA-Z\d ])>([a-zA-Z\d ])', '\g<1> greater than \g<2>', msg)
    msg = re.sub(r'([a-zA-Z\d ])<([a-zA-Z\d ])', '\g<1> less than \g<2>', msg)

    # Punctuation
    msg = re.sub(r'\.(com|org|net|info|biz|us)', ' dot \g<1>', msg)
    msg = re.sub(r'www\.', 'www dot ', msg)
    msg = re.sub(r'[:,\/\*.!?]',' ',msg)

    # at&t
    while True:
        match = re.search(r'(?:\b|^)(\w+)&(\w+)(?:\b|$)', msg)
        if match is None:
            break

        
        (first, last) = match.group(1, 2)

        # Seperate as Letters
        if (len(first) + len(last) < 6 ):
            (newfirst, newlast) = ( (' ').join(x) for x in (first, last) )
            msg = re.sub('(?:^|\b)' + first + '&' + last + '(?:\b|$)', newfirst + ' and ' + newlast, msg)
        
        # Seperate as words
        else:
            msg = re.sub('(?:^|\b)' + first + '&' + last + '(?:\b|$)', first + ' and ' + last, msg)       
    
    msg = re.sub('&', 'and', msg)

    # Hyphens
    msg = re.sub(r'-(\D|$)', ' \g<1>', msg)

    # Break into words
    syll = 0
    words = word_split(msg)

    # Count the syllables
    return sum([word_syll(x) for x in words])

# Returns words in a string
def word_split(txt):
    words = txt.split()
    return words

# Returns syllables for a word
def word_syll(word):

    # Remove casing
    word = word.lower()

    # String of a single letters
    if re.match(r'([a-z])\1*$', word):
        if re.match('[aeiou]', word):
            return 1
        elif re.match('w', word):
            return 3 * len(word)
        else:
            return len(word)

    # Acronyms
    if re.match('[bcdfghjklmnpqrstvwxz]+$', word):
        return len(word) + 2 * word.count('w')

    # Numbers
    if re.match('[0-9]+$', word):
        return number(word)
    elif re.match('-[0-9]+$', word):
        re.sub('-', '', word)
        return number(word) + 2

    # Check cheat sheet
    if word in syllcache.keys():
        return syllcache[word]

    # Check dictionary
    if word in d.keys():
        return [len(list(y for y in x if y[-1].isdigit())) for x in d[word]][0]

    # Calculate Syllables
    return calc(word)

# Algorithmically determines syllable count
def calc(word):

    # Strip Case
    word = word.lower()

    # Apostrophe
    word = re.sub('\'','',word)
 
    # Rule Arrays
    co_one = ['cool','coach','coat','coal','count','coin','coarse','coup','coif','cook','coign','coiffe','coof','court']
    co_two = ['coapt','coed','coinci']
    pre_one = ['preach']
 
    # Syllable Adjustment Counters
    syls = 0
    disc = 0
 
    # If < 3 chars, return 1
    if len(word) <= 3 :
        return 1
 
    # If doesn't end with "ted" or "tes" or "ses" or "ied" or "ies", discard "es" and "ed" at the end.
    # If it has only 1 vowel or 1 set of consecutive vowels, discard. (like "speed", "fled" etc.)
    if word[-2:] == "es" or word[-2:] == "ed" :
        doubleAndtripple_1 = len(re.findall(r'[eaoui][eaoui]',word))
        if doubleAndtripple_1 > 1 or len(re.findall(r'[eaoui][^eaoui]',word)) > 1 :
            if word[-3:] == "ted" or word[-3:] == "tes" or word[-3:] == "ses" or word[-3:] == "ied" or word[-3:] == "ies" :
                pass
            else :
                disc+=1
 
    # Discard trailing "e", except where ending is "le"
    le_except = ['whole','mobile','pole','male','female','hale','pale','tale','sale','aisle','whale','while']
    if word[-1:] == "e" :
        if word[-2:] == "le" and word not in le_except :
            pass
        else :
            disc+=1
 
    # Count vowel pairs and triplets as 1
    doubleAndtripple = len(re.findall(r'[eaoui][eaoui]',word))
    tripple = len(re.findall(r'[eaoui][eaoui][eaoui]',word))
    disc+=doubleAndtripple + tripple
 
    # Count remaining vowels
    numVowels = len(re.findall(r'[eaoui]',word))
 
    # Add 1 if starts with "mc"
    if word[:2] == "mc" :
        syls+=1
 
    # Add 1 if ends with "y" but is not surrouned by vowel
    if word[-1:] == "y" and word[-2] not in "aeoui" :
        syls +=1
 
    # Add 1 if "y" is surrounded by non-vowels and is not in the last word.
    for i,j in enumerate(word) :
        if j == "y" :
            if (i != 0) and (i != len(word)-1) :
                if word[i-1] not in "aeoui" and word[i+1] not in "aeoui" :
                    syls+=1
 
    # If starts with "tri-" or "bi-" and is followed by a vowel, add 1.
    if word[:3] == "tri" and word[3] in "aeoui" :
        syls+=1
    if word[:2] == "bi" and word[2] in "aeoui" :
        syls+=1
 
    # If ends with "-ian", should be counted as 2 syllables, except for "-tian" and "-cian"
    if word[-3:] == "ian" : 
        if word[-4:] == "cian" or word[-4:] == "tian" :
            pass
        else :
            syls+=1
 
    # If starts with "co-" and is followed by a vowel, check rule arrays
    if word[:2] == "co" and word[2] in 'eaoui' :
        if word[:4] in co_two or word[:5] in co_two or word[:6] in co_two :
            syls+=1
        elif word[:4] in co_one or word[:5] in co_one or word[:6] in co_one :
            pass
        else :
            syls+=1
 
    # If starts with "pre-" and is followed by a vowel, check rule arrays
    if word[:3] == "pre" and word[3] in 'eaoui' :
        if word[:6] in pre_one :
            pass
        else :
            syls+=1
 
    # Check for "-n't" and cross match with dictionary
    negative = ["doesn't", "isn't", "shouldn't", "couldn't","wouldn't"]
    if word[-3:] == "n't" :
        if word in negative :
            syls+=1
        else :
            pass
 
    # calculate the output
    count = numVowels - disc + syls
    plural = 's'
    if count == 1:
        plural = ''
    return count

# Return number of syllables in a number
def number(num):

    if num == '10' or num == '12':
        return 1
    if num == '0' or num == '00':
        return 2
    if num == '11':
        return 3

    count = 0;
    if len(num) > 15:
        count += int( ( len(num) - 13 ) / 3 )

    # 'oh three'
    if len(num) == 2:
        if num[0] == "0":
            return 1 + seven(num[1])

    place = 1
    futurecount = 0
    for digit in num[::-1]:
        if futurecount:
            count += futurecount
            futurecount = 0
        if place == 1:
            count += seven(digit)
        if place == 2:
            if digit == "0":
                count += 0
            elif digit == "1":
                count += 1
            else:
                count += 1 + seven(digit)
        if place == 3:
            if digit == "0":
                count += 0
            else:
                count += 2 + seven(digit)
        if place == 3:
            futurecount += 2
            place = 0
        place += 1

    return count;

def seven(digit):
    if digit == "7":
        return 2
    if digit == "0":
        return 0
    return 1