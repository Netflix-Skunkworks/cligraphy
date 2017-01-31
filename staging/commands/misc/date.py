#!/usr/bin/env python
# Copyright 2013 Netflix, Inc.

"""Date/Time tool with timezone support

Date/Time tool with timezone support
"""


import pytz
import tzlocal
import datetime
import calendar

DEFAULT_TIME_ZONES = ['Pacific/Honolulu',
                      'Pacific/Auckland',
                      'Australia/Sydney',
                      'Asia/Tokyo',
                      'America/Los_Angeles',
                      'America/Phoenix',
                      'America/Denver',
                      'America/Chicago',
                      'America/New_York',
                      'Europe/Dublin',
                      'Europe/London',
                      'Europe/Paris',
                      'Europe/Helsinki',
                      'Europe/Stockholm',
                      'Europe/Berlin',
                      ]


def pad(values, width):
    """Format a list of values to a certain width"""
    values = [ str(data) for data in values ]
    return ''.join([ data + (' ' * (width - len(data))) for data in values ])


def show(dt, show_zones):
    """Display a datetime object adjusted to the given timezones"""

    seen_zones = set()
    stamps = []

    def add(dt):  # pylint:disable=missing-docstring
        if dt.tzname() not in seen_zones:
            stamps.append(dt)
            seen_zones.add(dt.tzname())
    #
    add(dt)
    add(dt.astimezone(tzlocal.get_localzone()))
    add(dt.astimezone(pytz.utc))
    for tz in show_zones:
        add(dt.astimezone(pytz.timezone(tz)))

    stamps.sort(key=lambda x: int(x.strftime("%s")))

    for stamp in stamps:
        print pad((stamp.tzinfo.zone,
                  stamp.strftime("%H:%M:%S") + (' *' if stamp.tzinfo.zone == 'local' else ''),
                  stamp.strftime("%Z"),
                  stamp.strftime("%z"),
                  stamp.strftime("%A"),
                  stamp.strftime("%Y-%m-%d")), 24)

    print ''
    print 'Posix UTC timestamp:', calendar.timegm(dt.utctimetuple())


def configure(parser):
    parser.add_argument('-d', '--delta', metavar='DAYS', type=int, default=None,
                        help='delta in days, can be negative (eg. "-d -4" to show information for 4 days ago)')
    parser.add_argument('-l', '--localize', metavar='OLSONCODE', default=None,
                        help='force timezone (defaults to system local timezone, or UTC if a stamp is specified)')
    parser.add_argument('-z', dest='zones', metavar='OLSONCODE', nargs='+',
                        default=DEFAULT_TIME_ZONES,
                        help='show time in additional timezones')
    parser.add_argument('stamp', nargs='?', type=int, default=None,
                        help='unix timestamp to use (instead of now)')


def main(args):

    tz = None

    if args.stamp is not None:
        dt = datetime.datetime.utcfromtimestamp(args.stamp)
        tz = pytz.utc
    else:
        dt = datetime.datetime.now()

    if args.delta is not None:
        dt = dt + datetime.timedelta(days=args.delta)

    if args.localize:
        tz = pytz.timezone(args.localize)
    elif tz is None:
        tz = tzlocal.get_localzone()

    show(tz.localize(dt), show_zones=args.zones)
