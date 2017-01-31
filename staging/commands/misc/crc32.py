#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Compute crc32
"""

import zlib


def configure(parser):
    parser.add_argument('filename_list', metavar='FILENAME', nargs='+', help='Filename, or - for stdin')


def crc32(filename, filep):
    cksum = 0
    while True:
        data = filep.read(1024*1024)
        if not data:
            break
        cksum = zlib.crc32(data, cksum)
    print '%s %X' % (filename, cksum & 0xFFFFFFFF)


def main(args):
    for filename in args.filename_list:
        with open('/dev/stdin' if filename == '-' else filename, 'rb') as filep:
            crc32(filename, filep)
