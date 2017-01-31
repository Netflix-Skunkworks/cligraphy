#!/usr/bin/env python
# Copyright 2014 Netflix

"""Set a configuration key

Set a configuration key. By default, your custom configuration file will be modified.
"""


from cligraphy.core import ctx, find_node, write_configuration_file

TYPES = {
    'int': int,
    'float': float,
    'str': str,
    'bool': lambda value: value in ('true', 'True', '1', 'yes')
}


def configure(args):
    args.add_argument('--layer', type=str, default='custom', help='Perform operation on the specified configuration layer')
    args.add_argument('-t', '--type', type=str, default='str', help='value type', choices=TYPES.keys())
    args.add_argument('name', type=str, help='Configuration key path')
    args.add_argument('value', type=str, help='Value')


def main(args):
    root = ctx.cligraph.conf_layers[args.layer][1] or {}
    parts = args.name.split('.')
    node = find_node(root, parts[:-1], add=True)

    if node is None:
        print 'could not find key %s' % (args.name)
        return 1

    if node.get(parts[-1], None) == args.value:
        print '%s is already set to value %s' % (args.name, args.value)
        return 0

    node[parts[-1]] = TYPES[args.type](args.value)
    write_configuration_file(ctx.cligraph.conf_layers[args.layer][0], root)
