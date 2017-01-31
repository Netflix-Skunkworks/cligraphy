#!/usr/bin/env python
# Copyright 2013 Netflix

"""Run git gc on all repos"""

from nflx_oc.commands.dev.repos import run_for_all_repos


def configure(parser):
    parser.add_argument('--aggressive', help='Pass --aggressive to git gc', action='store_true', default=False)
    parser.add_argument('--fsck', help='Run git fsck before gc', action='store_true', default=False)


def main(args):
    if args.fsck:
        run_for_all_repos('git fsck')
    run_for_all_repos('git gc' + (' --aggressive' if args.aggressive else ''))
