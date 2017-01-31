#!/usr/bin/env python
# Copyright 2014 Netflix

"""Show current configuration

Show oc configuration. By default the effective (auto+shared+custom) configuration is shown.
"""

from cligraphy.core import ctx, dictify_recursive
import yaml
import logging


def configure(args):
    args.add_argument('--layer', type=str, default='', help='Only show the specified configuration layer')
    args.add_argument('--json', action='store_true', help='Output in json format')


def main(args):
    if args.layer:
        selected = ctx.cligraph.conf_layers[args.layer][1]
    else:
        selected = ctx.cligraph.conf

    if not selected:
        if args.layer:
            logging.error("No configuration defined at layer [%s]", args.layer)
        else:
            logging.error("No configuration defined")
        return

    selected = dictify_recursive(selected)

    if args.json:
        import json
        print json.dumps(selected, indent=4)
    else:
        print yaml.dump(selected, width=50, indent=4, default_flow_style=False)
