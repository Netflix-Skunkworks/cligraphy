#!/usr/bin/env python
# Copyright 2013, 2104 Netflix, Inc.


import argparse
import copy
import functools
import imp
import importlib
import json
import logging
import os
import os.path
import pkgutil
import sys
import time
from contextlib import contextmanager


try:
    import gevent.monkey as gevent_monkey
except ImportError:
    gevent_monkey = None

NO_HELP = 'No help :('

FUZZY_PARSED = []
RECENT_SUB_PARSERS = []
UNAVAILABLE_MODULES = []


class CustomDescriptionFormatter(argparse.RawTextHelpFormatter):

    def _get_help_string(self, action):
        help = action.help
        if '(default' not in help and type(action) not in (argparse._StoreConstAction, argparse._StoreTrueAction, argparse._StoreFalseAction):
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


class ParserError(Exception):

    def __init__(self, parser, message):
        self.parser = parser
        self.message = message

    def report(self, force_message=None):
        if RECENT_SUB_PARSERS:
            RECENT_SUB_PARSERS[-1].print_help(sys.stderr)
        else:
            self.parser.print_help(sys.stderr)
        sys.stderr.write('\n')
        if force_message:
            sys.stderr.write(force_message)
        else:
            sys.stderr.write('%s: error: %s\n' % (self.parser.prog, self.message))
        sys.exit(2)


def split_args(args):
    """Split command line args in 3 groups:
    - head, containing the initial options
    - body, containing everything after head, up to the first option
    - tail, containing everything after body
    """

    head = []
    body = []
    tail = []
    for arg in args:
        if arg.startswith('-'):
            if body:
                tail.append(arg)
            else:
                head.append(arg)
        else:
            if tail:
                tail.append(arg)
            else:
                body.append(arg)
    return head, body, tail


def attempt_fuzzy_matching(args, candidates):
    head, body, tail = split_args(args)

    if not body:
        return None, None

    import re
    matches = []

    while body:
        partial_body = body
        fuzzy_body = '.*'.join(partial_body)
        for candidate in candidates:
            if re.search(fuzzy_body, candidate):
                matches.append(candidate)
        if matches:
            break
        tail.insert(0, body.pop())

    if not matches:
        logging.debug('No fuzzy matches for command line args %s', args)
        return None, matches

    if len(matches) > 1:
        logging.debug('Multiple fuzzy matches for command line args %s: %s', args, matches)
        return None, matches

    new_args = []
    new_args.extend(head)
    new_args.extend(matches[0].split(' '))
    new_args.extend(tail)
    return new_args, matches


class BaseParser(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        argparse.ArgumentParser.__init__(self, *args, **kwargs)

    def error(self, message):
        raise ParserError(self, message)

    def parse_known_args(self, args=None, namespace=None):
        RECENT_SUB_PARSERS.append(self)
        return argparse.ArgumentParser.parse_known_args(self, args, namespace)

    def _check_value(self, action, value):
        if action.choices is not None and value not in action.choices:  # special handling for a nicer "choice" error message
            available = ', '.join(map(str, action.choices))
            if len(available) > 20:
                available = '\n%s' % available
            msg = 'Invalid choice [%s], choose from: %s' % (value, available)
            raise argparse.ArgumentError(action, msg)
        else:
            super(BaseParser, self)._check_value(action, value)


class SmartCommandMapParser(BaseParser):

    def __init__(self, *args, **kwargs):
        super(SmartCommandMapParser, self).__init__(*args, **kwargs)
        self.root_sub = self.add_subparsers(help='Available sub-commands', parser_class=BaseParser)
        self.sub_map = {'': self.root_sub}
        self.flat_map = {}

    def add_namespace(self, namespace, parent):
        desc = '%s sub-command group' % namespace.capitalize()
        temp = parent.add_parser(namespace,
                                 help=desc,
                                 description=desc,
                                 formatter_class=CustomDescriptionFormatter,
                                 add_help=False)
        temp.add_argument('-h', '--help', dest='_help', action=argparse._HelpAction)
        sub = temp.add_subparsers(help='Available sub-commands', parser_class=BaseParser)
        self.sub_map[namespace] = sub
        return sub

    def add_item(self, subparser, module_name, item, command_path):
        name, node = item
        if node.get('type') == 'cmd':
            parser = subparser.add_parser(name,
                                          help=node.get('help'),
                                          description=node.get('desc', node.get('help')),
                                          formatter_class=CustomDescriptionFormatter,
                                          add_help=False)
            if node.get('error'):
                def _func(*args, **kwargs):
                    logging.error('This command is unavailable: %s', node.get('desc'))
                    logging.error('NB: after fixing the issue, remember to run oc refresh again')
                    sys.exit(1)
                parser.set_defaults(_func=_func)
            else:
                parser.set_defaults(_func=functools.partial(finish_parser, copy.copy(parser), module_name + '.' + name))
            self.flat_map[(command_path + ' ' + name).strip()] = module_name + '.' + name
        else:
            sub = self.add_namespace(name, subparser)
            for sub_node in node.iteritems():
                self.add_item(sub, module_name + '.' + name, sub_node, command_path + ' ' + name)

    def add_command_map(self, namespace, command_map):
        sub = self.sub_map.get(namespace, None)
        if sub is None:
            sub = self.add_namespace(namespace, self.root_sub)

        module_name = command_map['module']
        for item in command_map['commands'].iteritems():
            self.add_item(sub, module_name, item, namespace)

    def pre_parse_args(self, args):
        """Perform our first pass parsing of the given command line arguments.
        Try fuzzy matching if we can't parse the command line as is.
        Return the final args (eg. possibly corrected after fuzzy matching) and the actual command function to be executed.
        """
        try:
            parsed_args, _ = self.parse_known_args(args)
        except ParserError as pe:
            # if we get 'too few arguments here', user is referencing a command group, and we shouldn't fuzzy match
            if pe.message == 'too few arguments':
                pe.report()
            logging.debug('Could not parse command line args [%s], attempting fuzzy matching', args)
            fixed_args, matches = attempt_fuzzy_matching(args, self.flat_map.keys())
            if fixed_args:
                logging.info('Your input "%s" matches "%s"', ' '.join(args), ' '.join(fixed_args))
                FUZZY_PARSED.append((' '.join(args), ' '.join(fixed_args)))
                args = fixed_args
                parsed_args, _ = self.parse_known_args(args)
            elif matches:
                message = 'Your command line matched the following existing commands:\n    %s\n' % ('\n    '.join(matches))
                pe.report(force_message=message)
            else:
                pe.report()

        return args, parsed_args._func()

    def parse_args(self, args=None):
        if args is None:
            args = sys.argv[1:]
        fixed_args, _ = self.pre_parse_args(args)
        return super(SmartCommandMapParser, self).parse_args(fixed_args)


def detect_monkey_patch():
    return gevent_monkey and len(gevent_monkey.saved) > 0


def error_module(module_name, exc):
    message = '%s: %s' % (exc.__class__.__name__, exc)
    UNAVAILABLE_MODULES.append((module_name, message))
    mod = imp.new_module(module_name)
    mod.__file__ = '__%s_error_stub__' % module_name
    mod.__doc__ = message
    mod.__error__ = True
    return mod

@contextmanager
def import_time_reporting(module_name):
    start = time.time()
    yield
    elapsed = time.time() - start
    if elapsed > 0.5:
        logging.info('slow import: module %s took %.2f seconds' % (module_name, elapsed))


def find_command_modules(prefix, path):
    """Returns a list of all command modules and packages"""
    prefix = '%s.' % (prefix)
    for loader, module_name, is_pkg in pkgutil.iter_modules(path, prefix=prefix):
        try:
            with import_time_reporting(module_name):
                mod = importlib.import_module(module_name)

            if detect_monkey_patch():
                logging.error('gevent monkey patching detected after module %s was loaded', module_name)
                raise Exception('monkey patching is not allowed in oc command modules')

            if getattr(mod, 'main', None):
                yield mod

            if is_pkg:
                with import_time_reporting(module_name):
                    pkg = importlib.import_module(module_name)
                for mod in find_command_modules(pkg.__name__, pkg.__path__):
                    yield mod
        except KeyboardInterrupt:
            raise
        except ImportError as ie:
            yield error_module(module_name, ie)
        except SyntaxError as se:
            yield error_module(module_name, se)
        except BaseException as be:
            yield error_module(module_name, be)


def finish_parser(parser, module_name):
    logging.debug('Build actual parser for module %s', module_name)
    module = importlib.import_module(module_name)

    if hasattr(module, 'configure'):
        module.configure(parser)

    parser.set_defaults(_func=module.main)
    parser.add_argument('-h', '--help', dest='_help', action=argparse._HelpAction)
    return module.main


class AutoDiscoveryCommandMap(object):
    """Automatically builds a commands map for our oc sub commands"""

    def __init__(self, cligraph, root_module_name):
        self.cligraph = cligraph
        self.root_node = {}
        self.package_nodes = {'': self.root_node}
        self.root_module_name = root_module_name

    def parse_help(self, module):
        """Parse docstring to generate usage"""
        doc = getattr(module, '__doc__', None)
        if doc is None:
            return NO_HELP, 'No description provided, you could add one! Code is probably located here: %s' % (module.__file__.replace('pyc', 'py'))
        else:
            halp, _, desc = doc.strip().replace('%', '%%').partition('\n')
            halp = halp.strip()
            if not desc:
                desc = halp
            return halp, desc

    def get_node(self, package_name):
        """Get or create a sub node"""
        logging.debug('Looking for package node [%s]', package_name)
        complete_package_name = package_name
        sub = self.package_nodes.get(package_name, None)
        if sub is None:
            logging.debug('-- not found')
            if '.' in package_name:
                parent_name, _, package_name = package_name.partition('.')
                parent = self.get_node(parent_name)
            else:
                parent = self.root_node

            sub = parent[package_name] = self.package_nodes[complete_package_name] = {}
        return sub

    def build(self, force_autodiscover=False):
        root_module = importlib.import_module(self.root_module_name)

        cached_command_map_filename = os.getenv('%s_COMMANDS_CACHE' % (self.cligraph.conf.tool.shortname.upper()),
                                                os.path.join(self.cligraph.conf.user.dotdir, 'commands.json'))
        if not force_autodiscover and os.path.exists(cached_command_map_filename):
            try:
                with open(cached_command_map_filename) as fpin:
                    command_map = json.load(fpin)
                return command_map
            except ValueError:
                logging.warning("Could not parse existing commands cache %s, ignoring it", cached_command_map_filename)

        for module in find_command_modules(self.root_module_name, root_module.__path__):
            package_name, _, module_name = module.__name__.rpartition('.')
            assert package_name.startswith(self.root_module_name)
            package_name = package_name[len(self.root_module_name)+1:]
            logging.debug('Configuring parser for %s.%s', package_name, module_name)
            halp, desc = self.parse_help(module)
            data = {'type': 'cmd', 'help': halp, 'desc': desc}
            if getattr(module, '__error__', False):
                data['error'] = True
            self.get_node(package_name)[module_name] = data

        if UNAVAILABLE_MODULES:
            logging.warning('The following modules are not available:')
            for name, msg in UNAVAILABLE_MODULES:
                logging.warning('    %s: %s', name, msg)

        command_map = {'module': self.root_module_name, 'commands': self.root_node}

        if os.access(os.path.dirname(cached_command_map_filename), os.W_OK) and (not os.path.exists(cached_command_map_filename)
                                                                                 or os.access(cached_command_map_filename, os.W_OK)):
            logging.debug('Writing command map json to %s', cached_command_map_filename)

            cached_command_map_filename_new = cached_command_map_filename + '.new'
            with open(cached_command_map_filename_new, 'w') as fpout:
                json.dump(command_map, fpout, indent=4)
            os.rename(cached_command_map_filename_new, cached_command_map_filename)
        else:
            logging.warning('Not updating commands cache (%s is not writeable)', cached_command_map_filename)
            logging.warning('Tip: are you using a shared install of octools? If so, no need to run oc refresh.')

        return command_map
