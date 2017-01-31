#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Human-friendly time period parsing
"""

import time
import math
from datetime import datetime
from dateutil import parser

UNITS = {
    'month': 3600*24*31,  # FIXME 1 month is not really 31 days
    'week': 3600*24*7,
    'day': 3600*24,
    'hour': 3600,
    'minute': 60,
    'second': 1,
}

UNITS['mon'] = UNITS['month']
UNITS['w'] = UNITS['week']
UNITS['d'] = UNITS['day']
UNITS['h'] = UNITS['hour']
UNITS['min'] = UNITS['minute']
UNITS['m'] = UNITS['minute']
UNITS['sec'] = UNITS['second']
UNITS['s'] = UNITS['second']

def parse_time(human_time):
    """Parse a human-friendly time expression, such as 1d or now, and return a unix timestamp
    """
    human_time = human_time.lower()
    now = int(time.time())
    if human_time == 'now':
        return now
    try:
        unit = human_time[-1]
        value = int(human_time[:-1])
        return now - (value * UNITS[unit])
    except:
        raise Exception('Dont know what to do with time [%s]' % human_time)

def parse_datetime(human_time):
    """Parse a human-friendly time expression (such as 1d or now)
            or datetime formatted as string (such as 2016-01-20 20:00)
        and return a datetime object
    """
    try:
        return datetime.fromtimestamp(parse_time(human_time))
    except:
        try:
            dt = parser.parse(human_time)
            return dt
        except:
            raise Exception('Dont know what to do with time [%s]' % human_time)

def align_times(start, end, ratio=0.02):
    """Align timestamps on a reasonable boundary
    """
    assert start < end, 'Start time must be before end time'
    boundary = int(math.ceil((end - start) * ratio))
    return int(start / boundary) * boundary, int(end / (boundary + 1)) * (boundary + 1)
