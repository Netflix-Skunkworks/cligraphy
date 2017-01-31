#!/usr/bin/env python
# Copyright 2014 Netflix

"""Edit local oc configuration
"""

import os
from cligraphy.core import edit_configuration

def main(args):
    def do(filename):
        os.system('$EDITOR %s' % filename)
    edit_configuration('oc', do)
