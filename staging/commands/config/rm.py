#!/usr/bin/env python
# Copyright 2014 Netflix

"""Remove a configuration key

Remove a configuration key. By default, your custom configuration file will be modified.
"""


from cligraphy.core import ctx, find_node, write_configuration_file
import collections


def configure(args):
    args.add_argument('-f', '--force', action='store_true', help='force deletion (of eg. keys that have sub-keys)')
    args.add_argument('--layer', type=str, default='custom', help='Perform operation on the specified configuration layer')
    args.add_argument('name', type=str, help='Configuration key path')


def main(args):
    root = ctx.cligraph.conf_layers[args.layer][1]
    parts = args.name.split('.')
    node = find_node(root, parts[:-1])

    if node is None or parts[-1] not in node:
        print 'no such configuration key %s' % (args.name)
        return 1

    value = node.pop(parts[-1])
    if isinstance(value, collections.Mapping) and not args.force:
        print 'key %s has sub keys, not removing. use -f to force.' % (args.name)
        return 2

    write_configuration_file(ctx.cligraph.conf_layers[args.layer][0], root)
