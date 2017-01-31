#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""A noop command for testing"""

import time
import logging


def configure(parser):
    parser.add_argument('sleep', nargs='?', type=int)


def main(args):
    if args.sleep:
        logging.info('Sleeping %d seconds', args.sleep)
        time.sleep(args.sleep)
