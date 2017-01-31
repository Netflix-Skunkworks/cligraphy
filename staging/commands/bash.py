#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2015 Netflix, Inc.

"""Run bash inside the octools environment."""

import os
import tempfile

RC = r"""
export PS1="\u@\h:\w> "

echo "Activating octools with ${CLIGRAPHY_REPO_PATH}/shell/oc_bash_profile.sh ..."
source ${CLIGRAPHY_REPO_PATH}/shell/oc_bash_profile.sh

cd ${CLIGRAPHY_REPO_PATH}
"""

def bash(command=None):
    """Start bash a custom rc file"""
    with tempfile.NamedTemporaryFile() as tmpfp:
        tmpfp.write(RC)
        tmpfp.flush()
        final_command = '/usr/bin/env bash --noprofile --rcfile %s' % tmpfp.name
        if command:
            final_command += (' -c %s' % command)
        os.system(final_command)


def configure(parser):
    parser.add_argument('-c', '--command', help='Command to be executed (with bash -c, instead of starting an interactive shell)')

def main(args):
    bash(args.command)
