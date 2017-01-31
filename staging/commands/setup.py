#!/usr/bin/env python
# Copyright 2013 Netflix, Inc.

"""Run setup

Runs all setup steps (or just a subset)
"""

import os


def configure(parser):
    parser.add_argument('fragment', nargs='*', help='fragment to setup')


def main(args):
    os.system('${CLIGRAPHY_REPO_PATH}/setup/setup %s' % ' '.join((args.fragment)))
