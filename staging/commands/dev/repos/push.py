#!/usr/bin/env python
# Copyright 2013 Netflix


"""Push all repos to stash
"""

from nflx_oc.commands.dev.repos import run_for_all_repos


def main():
    run_for_all_repos('git push origin master')
