#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

from cligraphy.core.capture import fmt_capnp

import time
import sys


def configure(parser):
    parser.add_argument('-s', '--speedup', help='Speedup factor', default=1.0, type=float)
    parser.add_argument('filename')


def main(args):
    player = fmt_capnp.CapnpSessionPlayer(args.filename)
    print player.session

    #for e in player.session_capnp.Event.read_multiple_packed(player.fpin):
    #    print e

    for interval, data in player.play():
        time.sleep(interval/args.speedup)
        if data is not None:
            sys.stdout.write(data)
            sys.stdout.flush()
