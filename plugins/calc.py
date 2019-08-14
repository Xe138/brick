# Math plugin
# Version 1.0.0
from __future__ import division
import re
import collections

def main(bag, config):

    # All valid expression characters
    match = re.match('(\-?\d[\s0-9a-fA-F_x\^+\-\*%/.()]+\d)$', bag['msg'])

    # Fix multiplication with 'x'
    exp = bag['msg']
    exp = re.sub('([1-9\s]+)x', '\g<1>*', exp, 0, re.I)

    # Fix exponents
    exp = re.sub('\^', '**', exp)

    # Check for invalid operations
    if re.search('\*\s+\*|\%\s*\%|\*\*\*|/\s+/|///', exp):
        return

    # Check for operator
    if (bag['addressed'] and re.search('[+\-*%/]', exp)) and match != None:

        # Check for invalid Hex notation
        numbers = re.findall('[x0-9a-fA-F.]+', exp)
        for num in numbers:
            if not re.match('0x|[0-9.]+$|[0-9.]+[eE][0-9]+$', num):
                print('Invalid Hex detected')
                return

        # Balance Parenthesis
        d = collections.defaultdict(int)
        for c in exp:
            d[c] += 1
        bal = d['('] - d[')']
        if bal > 0:
            print('Correcting unbalanced parenthesis')
            exp += ')' * bal
        elif bal < 0:
            print('Correcting unbalanced parenthesis')
            bal = bal * -1
            exp = '(' * bal + exp

        ans = eval(exp)
        return str(ans)