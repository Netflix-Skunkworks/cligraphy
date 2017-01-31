#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""
Cligraphy tools
"""

from attrdict import AttrDict

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

import collections
import os
import os.path
import re
import logging


class Context(object):

    def __init__(self):
        self._cligraph = None

    @property
    def cligraph(self):
        return self._cligraph

    @cligraph.setter
    def cligraph(self, value):
        self._cligraph = value

    @property
    def conf(self):
        return self._cligraph.conf

    @property
    def parser(self):
        return self._cligraph.parser



ctx = Context()


__CONF_SUBST_RE = re.compile(r'(%cfg.([a-zA-Z0-9.-_]+)%)')


def dictify_recursive(obj):
    """Transforms an attrdict tree into regular python dicts"""
    for key, val in obj.iteritems():
        if isinstance(val, AttrDict):
            obj[key] = dictify_recursive(val)
    return dict(**obj)


def update_recursive(base, overlay):
    """Resursively update base with values from overlay
    """
    for key, val in overlay.iteritems():
        if isinstance(val, collections.Mapping):
            base[key] = update_recursive(base.get(key, {}), val)
        else:
            base[key] = overlay[key]
    return base


def find_node(node, path, add=False):
    """Find a node in a dict tree. Path is the broken down path (array). Add missing nodes if add=True."""
    for part in path:
        if not node or not part in node:
            if add:
                node[part] = {}
            else:
                return None
        node = node[part]
    return node


def get(root, confkey):
    """Config key getter"""
    return find_node(root, confkey.split('.'))


def _resolve_config(root, subst_re, node=None):
    """recursive helper for resolve_config"""
    if node is None:
        node = root
    remaining = []
    for key, val in node.iteritems():
        if isinstance(val, collections.Mapping):
            remaining.extend(_resolve_config(root, subst_re, node=val))
        elif isinstance(val, basestring):
            for match, confkey in subst_re.findall(val):
                confval = get(root, confkey)
                if confval is not None and (not isinstance(confval, basestring) or subst_re.search(confval) is None):
                    node[key] = val = val.replace(match, str(confval))
                else:
                    remaining.append('%s: %s' % (key, val))
    return remaining


def resolve_config(cfg):
    """performs variable substitution in a configuration tree"""
    remaining = []
    for _ in range(16):  # 16 maximum substitution passes
        remaining_prev = remaining
        remaining = _resolve_config(cfg, __CONF_SUBST_RE)
        if not remaining or len(remaining) == len(remaining_prev):
            break
    if remaining:
        raise Exception('Incorrect configuration file: could not resolve some configuration variables:  %s' % remaining)


def automatic_configuration(cligraph, layer_name):
    auto_data = {
        'tool': {
            'name': cligraph.tool_name,
            'shortname': cligraph.tool_shortname,
            'version': '1.0',
            'repo_path': cligraph.tool_path,
        },
        'repos': {
            'root': os.path.abspath(os.path.join(cligraph.tool_path, '..')),
        },
    }
    username = os.getenv('USER')
    if username:
        auto_data['user'] = {
            'name': username,
            'email': '%s@domain.net' % (username)  # OPEN SOURCE TODO
        }
    else:
        auto_data['user'] = {
            'name': 'unknown',
            'email': 'octools-unknown-user@domain.net'  # OPEN SOURCE TODO
        }
    auto_data['user']['dotdir'] = os.path.abspath(os.path.expanduser('~/.' + cligraph.tool_shortname))
    return auto_data


def read_configuration(cligraph, custom_suffix=''):
    """Read configuration dict for the given tool
    """

    cfg = {}
    layers = collections.OrderedDict()
    layers['auto'] = [automatic_configuration, None]
    layers['shared'] = [os.path.join(cligraph.tool_path, 'conf/%s.yaml' % cligraph.tool_shortname), None]
    layers['custom'] = [os.path.join(os.path.abspath(os.path.expanduser('~/.' + cligraph.tool_shortname)), '%s.yaml%s' % (cligraph.tool_shortname, custom_suffix)), None]

    for layer_name, layer_data in layers.items():
        if callable(layer_data[0]):
            layer = layer_data[0](cligraph, layer_name)
        else:
            if not os.path.exists(layer_data[0]):
                continue
            with open(layer_data[0], 'r') as filep:
                layer = yaml.load(filep, Loader=Loader)
        layers[layer_name][1] = layer
        if layer:
            update_recursive(cfg, layer)

    resolve_config(cfg)
    return AttrDict(**cfg), layers


def write_configuration_file(filename, conf):
    """Write a config dict to the specified file, in yaml format"""
    import shutil

    try:
        shutil.copy2(filename, '%s.back' % filename)
    except IOError:
        pass

    try:
        os.makedirs(os.path.dirname(filename))
    except OSError:
        pass

    with open(filename, 'w') as filep:
        yaml.dump(conf, filep, indent=4, default_flow_style=False, Dumper=Dumper)


def edit_configuration(tool_name, callback):
    """Wrapper for configuration editing tools
    """
    import shutil

    filename = os.path.join(USER_DOTDIR, '%s.yaml' % tool_name)
    edit_filename = '%s.edit' % filename

    if os.path.exists(edit_filename):
        logging.warn('Unfinished edit file %s exists, editing that one.', edit_filename)
    else:
        if os.path.exists(filename):
            shutil.copy2(filename, edit_filename)
        else:
            with open(edit_filename, 'w') as fp:
                fp.write('\n')

    callback(edit_filename)

    read_configuration(tool_name, custom_suffix='.edit')  # validate that configuration is still readable

    if os.path.exists(filename):
        shutil.copy2(filename, '%s.back' % filename)
    os.rename(edit_filename, filename)
