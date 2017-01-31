#!/usr/bin/env python
# Copyright 2013 Netflix


"""Test your code!
nosetests wrapper
"""

import os


def configure(args):
    args.add_argument('-c', '--coverage', help='Show test coverage', action='store_true')
    args.add_argument('-v', '--verbose', help='Verbose output', action='store_true')


def main(args):
    command = ['nosetests']

    if args.coverage:
        command.append('--with-coverage')

    if args.verbose:
        command.append('--verbose')

    os.system(' '.join(command))
