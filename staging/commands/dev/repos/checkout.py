#!/usr/bin/env python
# Copyright 2013 Netflix


"""Check out OC repositories
"""


from cligraphy.core import ctx
import logging
import os


def main():
    for repo, origin in ctx.conf.repos.list.items():
        dest = '%s/%s' % (ctx.conf.repos.root, repo)
        if not os.path.exists(dest):
            os.system('git clone %s %s' % (origin, dest))
        else:
            logging.debug("%s already exists, not cloning", dest)
