#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Check syntax
"""

import json
import yaml


def autodetect(filename, filep):
    """Try to detect language based on filename extension"""
    ext = filename.rpartition('.')[-1]
    checker = LANGUAGES.get(ext, None)
    if checker is None:
        raise Exception('Unknown file extension [%s]' % ext)
    checker(filename, filep)


def json_check(_, filep):
    """Parses json to find syntax errors"""
    try:
        json.load(filep)
    except ValueError as exc:
        print 'JSON syntax error: %s' % exc


def yaml_check(_, filep):
    """Parses yaml to find syntax errors"""
    try:
        yaml.load(filep)
    except yaml.scanner.ScannerError as exc:
        print 'YAML syntax error: %s -%s' % (exc.problem, exc.problem_mark)


LANGUAGES = {
    'auto': autodetect,
    'json': json_check,
    'yaml': yaml_check
}


def configure(parser):
    parser.add_argument('-l', dest='checker', default='auto', choices=LANGUAGES.keys())
    parser.add_argument('filenames', metavar='FILENAME', nargs='+')


def main(args):
    for filename in args.filenames:
        with open(filename, 'rb') as filep:
            LANGUAGES[args.checker](filename, filep)
