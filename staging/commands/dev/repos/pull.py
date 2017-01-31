#!/usr/bin/env python
# Copyright 2013 Netflix


"""Pull all repos from stash
"""

from nflx_oc.commands.dev.repos import run_for_all_repos


def main():
    run_for_all_repos('git pull')
