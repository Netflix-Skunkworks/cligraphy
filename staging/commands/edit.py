#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Edit an oc command

Open the source code for an oc command in your $EDITOR
"""


import os
import os.path
import logging

from cligraphy.core import ctx
from cligraphy.core import decorators


def configure(parser):
    parser.add_argument('-p', '--path', help='just show the path of the file that would be edited', action='store_true')
    parser.add_argument('terms', nargs='+', metavar='term', help='oc command (as a fuzzy sequence of terms, eg: oca log search)')


@decorators.tag(decorators.Tag.interactive)
def main(args):
    import cligraphy.core.cli
    import cligraphy.core.parsers
    from cligraphy.core.parsers import SmartCommandMapParser
    from cligraphy.core.util import undecorate_func

    parser = SmartCommandMapParser()
    for namespace, command_map in ctx.cligraph.get_command_maps():
        parser.add_command_map(namespace, command_map)

    _, func = parser.pre_parse_args(args.terms)
    orig_func, _ = undecorate_func(func)
    filename = orig_func.__code__.co_filename

    print 'Command is defined in %s inside folder %s' % (filename, os.path.dirname(filename))
    if not args.path:
        logging.info('Editing %s', filename)
        editor = ctx.conf.get('editor', os.getenv('EDITOR', None))
        assert editor is not None, 'You have no configured editor - define $EDITOR or run eg. "oc conf add editor vim"'
        os.system('%s %s' % (editor, filename))
