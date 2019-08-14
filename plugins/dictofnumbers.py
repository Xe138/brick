# Finds contextual numbers
# Version 1.0.4
import re
import json
import pint
import string
import random

from pint import UnitRegistry
ureg = UnitRegistry('lib/dictofnumbers/unit_def.txt', autoconvert_offset_to_baseunit=True)

data = None
units = None
width = 10

unit_table = {
    'kgs' : 'kg',
    'hz'  : 'hertz',
    'in'  : None
}

base_units = {
        'usd'                                           : '$',
        'ampere'                                        : 'A',
        'hertz'                                         : 'Hz',
        'coulomb'                                       : 'C',
        'lumen'                                         : 'lm',
        'kilogram'                                      : 'kg',
        'kilogram / meter ** 3'                         : 'kg/m^3',
        'ohm'                                           : 'ohm',
        'meter / second'                                : 'm/s',
        'meter / second ** 2'                           : 'm/s^2',
        'joule'                                         : 'J',
        'meter'                                         : 'm',
        'newton'                                        : 'N',
        'second'                                        : 's',
        'tesla'                                         : 'T',
        'watt'                                          : 'W',
        'volt'                                          : 'V',
        'meter ** 2'                                    : 'm^2',
        'kilogram * meter ** 2 / kelvin / second ** 2'  : 'J/K',
        'kelvin'                                        : 'K',
        'people'                                        : 'people'
    }

# initialize function
def init():
    global data
    global units

    # Load data
    db = 'lib/dictofnumbers/dictofnumbers.json'
    json_data=open(db).read()
    data = json.loads(json_data)

    # Get Units
    units = data.keys()

    # Construct Ranges
    for x in units:
        for y in data[x]:
            y['low']  = y['number'] * (100 - width) / 100
            y['high'] = y['number'] * (100 + width) / 100

    print('Dictionary of Numbers Initialized.')

def getContext(val, unit):

    # Lookup Units
    if unit in unit_table.keys():
        unit = unit_table[unit]

    if not unit:
        return []

    # Generate Quantity
    try:
        qty = val * ureg.parse_expression(unit)
    except pint.UndefinedUnitError as e:
        return []

    # Convert Units
    qty = convertUnits(qty)

    # Lookup DB Units
    if str(qty.units) in base_units.keys():
        db_unit = base_units[str(qty.units)]
    else:
        print('Dict of Numbers Error: Base Unit ' + repr(qty.units) + ' not found!')
        return []

    # Unit check
    if db_unit not in units:
        print('Dict of Numbers Error: DB Unit ' + repr(db_unit) + ' not found!')
        return []

    # Get Context
    context = []
    magnitude = float(qty.magnitude)
    for x in data[db_unit]:
         if magnitude >= x['low'] and magnitude <= x['high']:
            context.append(x)

    if len(context):
        return { 'val' : val, 'unit' : unit, 'context' : context, '_unit' : db_unit, '_val' : magnitude }

    return []
    

# Converts a given value to standardized units
def convertUnits(qty):

    # Standardize Units
    qty.ito_base_units()

    # Convert sec^-1 to Hz
    if qty.units == (1 / ureg.second).units or qty.units == (ureg.radian / ureg.second).units:
        qty.ito(ureg.hertz)
    # Convert A-s t0 C
    elif qty.units == (ureg.ampere * ureg.second).units:
        qty.ito(ureg.coulomb)
    # Convert cd*rad to lm
    elif qty.units == (ureg.candela * ureg.radian ** 2).units:
        qty.ito(ureg.lumen)
    # Convert gram to kg
    elif qty.units == ureg.gram.units:
        qty.ito(ureg.kilogram)
    # Convert g/m^3 to kg/m^3
    elif qty.units == (ureg.gram / ureg.meter ** 3).units:
        qty.ito(ureg.kilogram / ureg.meter ** 3)
    # Convert g-m^2/A^2-s^3 to ohms
    elif qty.units == (ureg.gram * ureg.meter ** 2 / ureg.ampere ** 2 / ureg.second ** 3).units:
        qty.ito(ureg.ohm)
    # Convert g-m^2/s^2 to joules
    elif qty.units == (ureg.gram * ureg.meter ** 2 / ureg.second ** 2).units:
        qty.ito(ureg.joule)
    # Convert g-m/s^2 to newtons
    elif qty.units == (ureg.gram * ureg.meter / ureg.second ** 2).units:
        qty.ito(ureg.newton)
    # Convert g/A-s^2 to teslas
    elif qty.units == (ureg.gram / ureg.ampere / ureg.second ** 2).units:
        qty.ito(ureg.tesla)
    # Convert g-m^2/s^3 to watts
    elif qty.units == (ureg.gram * ureg.meter ** 2 / ureg.second ** 3).units:
        qty.ito(ureg.watt)
    # Convert g-m^2/A-s^3 to volts
    elif qty.units == (ureg.gram * ureg.meter ** 2 / ureg.ampere / ureg.second ** 3).units:
        qty.ito(ureg.volt)
    # Convert g-m^2/K-s^2 to g-m^2/K-s^2 (J/K)
    elif qty.units == (ureg.gram * ureg.meter ** 2 / ureg.kelvin / ureg.second ** 2).units:
        qty.ito(ureg.kilogram * ureg.meter ** 2 / ureg.kelvin / ureg.second ** 2)

    return qty


def main(bag, config):

    # Isolate Values
    values = []
    match = re.finditer('(\$)?([\d,]+(?:\.\d+)?)\s*(\S+)?', bag['msg'])
    for x in match:
        val  = x.group(2).replace(',', '')
        if x.group(1):
            unit = 'USD'
        elif x.group(3):
            unit = x.group(3).rstrip(string.punctuation)
        else:
            continue

        if len(val):
            values.append({'val' : float(val), 'unit' : unit})

    # Get Context Values
    context = []
    for x in values:
        if x['val'] and x['unit']:

            # Ignore invalid units
            if unitcheck(x['unit']):
                context.append(getContext(x['val'], x['unit']))

    context = [x for x in context if x != []]

    if not len(context):
        return

    # Compile Response
    context = random.choice(context)
    subj = string_num(context['val']) + ' ' + context['unit']
    context['context'] = random.choice(context['context'])
    resp = subj + ' is about the ' + context['context']['text'] + '.'
    
    # Compile Source
    source = ""
    if context['val'] != context['_val'] or context['unit'] != context['_unit']:
        source += subj + ' => ' + str(context['_val']) + ' ' + context['_unit'] + '\n'
    source += context['context']['text'] + ' => ' + str(context['context']['number']) + ' ' + context['context']['unit'] + '\n'
    source += 'source: ' + context['context']['source']

    return { 'msg' : resp, 'last' : {'response' : source} }


# Check for valid units
def unitcheck(unit):

    if re.match('[\+\-\*/]', unit):
        return False

    return True


# Converts a number point to a string with no decimal places
def string_num(val):
    val = round(val)
    num = "{:,}".format(val)
    num = re.sub('\.0*', '', num)
    return num

# Prints JSON data
def jprint(data):

    print(json.dumps(data, indent=4, sort_keys=True))

init()