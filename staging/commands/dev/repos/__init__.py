#!/usr/bin/env python
# Copyright 2014 Netflix

"""
Repos commands

Source code repos related commands
"""

import os
from cligraphy.core import ctx


def run_for_all_repos(shell_command):
    """Run the given command in each repository"""
    for repo in ctx.conf.repos.list.keys():
        print '='*12, repo
        os.system('cd %s/%s && %s' % (ctx.conf.repos.root, repo, shell_command))
        print ''
