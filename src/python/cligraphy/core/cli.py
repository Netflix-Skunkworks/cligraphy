#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright 2013 Netflix, Inc.


"""Command line tools entry point."""

from cligraphy.core import capture, decorators, read_configuration, ctx
from cligraphy.core.log import setup_logging
from cligraphy.core.parsers import AutoDiscoveryCommandMap, SmartCommandMapParser, ParserError, CustomDescriptionFormatter
from cligraphy.core.util import undecorate_func, pdb_wrapper, profiling_wrapper, call_chain

from remember.memoize import memoize

import faulthandler
from setproctitle import setproctitle  # pylint:disable=no-name-in-module

import argcomplete
import argparse
import logging
import logging.config
import os
import signal
import subprocess
import sys


def _warn_about_bad_non_ascii_chars(args):
    """Detect non-ascii variants of some interesting characters, such as — instead of -"""
    bad_chars = (
        u'—',
        u'…',
        u'“',
        u'”',
        u'\u200b',  # zero-width space
    )
    try:
        line = ' '.join(arg.decode(sys.stdout.encoding or 'UTF-8') for arg in args)
        bad = [ char in bad_chars for char in line ]
        if any(bad):
            logging.warning('Your command line contains %d bad unicode character(s), did you copy/paste from a tool that garbles text?', len(bad))
            logging.warning('> ' + line)
            logging.warning('> ' + ''.join('^' if isbad else ' ' for isbad in bad))
            return
    except Exception:  # pylint:disable=broad-except
        logging.warning('Exception while trying to detect bad unicode characters in command line args; continuing...', exc_info=True)


def _warn_about_bad_path(env_root, path):
    """Warn about mistakes in $PATH"""
    if not env_root:
        logging.warning('Running oc outside of its virtualenv is supported, but untested. Please report any bugs!')
        return
    env_bin = os.path.join(env_root, 'bin')
    elements = path.split(':')
    try:
        position = elements.index(env_bin)
        if position != 0:
            logging.warning('Your oc virtualenv, %s, is not the first element of your $PATH. Things might be broken.', env_root)
    except ValueError:
        logging.warning('Your oc virtualenv, %s, is not listed in your $PATH. Things are likely broken.', env_root)
        return



class _VersionAction(argparse.Action):
    """Shows last commit information"""
    def __call__(self, *args, **kwargs):
        try:
            os.chdir(ctx.conf.tool.repo_path)
            last_commit = subprocess.check_output(['git', 'log', '-1'], stderr=subprocess.PIPE)
        except (subprocess.CalledProcessError, OSError):
            last_commit = '(could not get more recent commit information)'
        print '%s v%s\n%s' % (ctx.conf.tool.name, ctx.conf.tool.version, last_commit)
        sys.exit(1)


class Cligraph(object):

    def __init__(self, name, shortname, path):
        assert name
        assert shortname
        assert path
        self.tool_name = name
        self.tool_shortname = shortname
        self.tool_path = path
        self.conf, self.conf_layers = read_configuration(self)
        ctx.cligraph = self


    # FIXME(stf/oss): header names for octools
    def _setup_requests_audit_headers(self, command):
        """Setup requests user-agent and x-user/x-app headers.
        Just best effort - we don't care that much if this fails"""
        try:
            import requests
            def _default_user_agent(*args):
                return 'requests (cligraphy/%s)' % command
            requests.utils.default_user_agent = _default_user_agent

            base_default_headers = requests.utils.default_headers
            def _default_headers(*args):
                headers = base_default_headers()
                headers['X-User'] = os.getenv('USER')
                headers['X-App'] = 'cligraphy/%s' % command
                return headers
            requests.utils.default_headers = _default_headers
            requests.sessions.default_headers = _default_headers
        except:
            logging.warn("Could set up requests audit headers, continuing anyway")
            pass

    # pylint:disable=protected-access
    def _run(self, args):
        """Run command by calling the main() function correctly (how we pass args depends on its actual signature)."""
        # if the main method has been decorated, we need to look at the original function's argspec (but call the wrapper)
        import inspect
        orig_func, _ = undecorate_func(args._func)
        argspec = inspect.getargspec(orig_func)
        if len(argspec.args) == 0:
            return args._func()
        elif argspec.varargs or argspec.keywords or len(argspec.args) > 1:
            kwargs = dict(**vars(args))
            for kw in kwargs.keys():
                if kw.startswith('_'):
                    logging.debug('removing internal arg %s', kw)
                    del kwargs[kw]
            return args._func(**kwargs)
        else:
            if argspec.args[0] != 'args':
                raise Exception('Programming error in command: if main() only has one argument it must be called "args"')
            func = args._func
            for kw in vars(args).keys():
                if kw.startswith('_') and kw not in ('_parser', '_cligraph'):  #FIXME(stf/oss) maybe just expose cligraph
                    logging.debug('removing internal arg %s', kw)
                    delattr(args, kw)
            return func(args)


    def _run_command_process(self, args):
        """Command (child) process entry point. args contains the function to execute and all arguments."""

        setup_logging(args._level)

        command = ' '.join(sys.argv[1:])
        setproctitle('oc/command/%s' % command)
        faulthandler.register(signal.SIGUSR2, all_threads=True, chain=False)  # pylint:disable=no-member
        self._setup_requests_audit_headers(command)

        ret = 1
        try:
            chain = [self._run]
            if args._profile:
                chain.append(profiling_wrapper)
            if args._pdb:
                chain.append(pdb_wrapper)
            ret = call_chain(chain, args)
        except SystemExit as exc:
            ret = exc.code
        except ParserError as pe:
            pe.report()
        except Exception:  # pylint:disable=broad-except
            logging.exception('Top level exception in command process')
        finally:
            sys.exit(ret)


    def _parse_args(self):
        """Setup parser and parse cli arguments.
        NB! counter-intuitively, this function also messes around with logging levels.
        """

        # We want some of our options to take effect as early as possible, as they affect command line parsing.
        # For these options we resort to some ugly, basic argv spotting

        if '--debug' in sys.argv:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.debug('Early debug enabled')

        if '--verbose' in sys.argv or '-v' in sys.argv:
            logging.getLogger().setLevel(logging.INFO)

        autodiscover = False
        if '--autodiscover' in sys.argv:
            logging.debug('Autodiscover enabled')
            autodiscover = True

        parser = SmartCommandMapParser(prog=self.tool_shortname,
                                       description="Cligraphy command line tools",
                                       formatter_class=CustomDescriptionFormatter)

        self.parser = parser  # expose to eg. ctx

        parser.add_argument('--version', action=_VersionAction, nargs=0, dest="_version")
        parser.add_argument("--debug", help="enable debuging output", dest="_level", action="store_const", const=logging.DEBUG)
        parser.add_argument("--pdb", help="run pdb on exceptions", dest="_pdb", action="store_true")
        parser.add_argument("--no-capture", help="(DEPRECATED) disable input/output capture", dest="_capture_deprecated", action="store_false", default=True) # DEPRECATED; left behind to avoid breaking existing references
        parser.add_argument("--enable-capture", help="enable input/output capture", dest="_capture", action="store_true", default=False)
        parser.add_argument("--no-reporting", help="disable reporting", dest="_reporting", action="store_false", default=True)
        parser.add_argument("--profile", help="enable profiling", dest="_profile", action="store_true", default=False)
        parser.add_argument("--autodiscover", help="re-discover commands and refresh cache (default: read cached commands list)", dest="_autodiscover", action="store_true")
        parser.add_argument("-v", "--verbose", help="enable informational output", dest="_level", action="store_const", const=logging.INFO)

        for namespace, command_map in self.get_command_maps(autodiscover):
            parser.add_command_map(namespace, command_map)

        argcomplete.autocomplete(parser)

        _warn_about_bad_non_ascii_chars(sys.argv)
        _warn_about_bad_path(os.getenv('VIRTUAL_ENV'), os.getenv('PATH'))

        args = parser.parse_args()
        args._parser = parser  # deprecated

        # pylint:disable=protected-access
        if args._level is not None:
            logging.getLogger().setLevel(args._level)

        return args

    @memoize()
    def get_command_maps(self, autodiscover=False):
        """Get all the command maps defined in our configuration.

        If autodiscover is True (defaults to False), python commands will be autodiscovered (instead of simply being obtained
        from a cached command map)."""

        result = []
        for module, options in self.conf.commands.items():
            try:
                if options is None:
                    options = {}
                logging.debug('Configuring commands module %s with options %s', module, options)

                opt_type = options.get('type', 'python')
                opt_namespace = options.get('namespace', '')

                if opt_type == 'python':
                    result.append((opt_namespace, AutoDiscoveryCommandMap(self, module).build(force_autodiscover=autodiscover)))
                else:
                    raise Exception('Dont know how to handle commands module with type [%s]', opt_type)
            except Exception as exc:  # pylint:disable=broad-except
                logging.warning('Could not configure commands module [%s] defined in configuration: %s. Skipping it.', module, exc,
                                exc_info=True)

        return result

    def main(self):
        """Main oc wrapper entry point."""

        setup_logging()

        try:
            args = self._parse_args()
            logging.debug("Parsed args: %r", vars(args))
        except ParserError as pe:
            pe.report()

        if not os.isatty(sys.stdin.fileno()) or not os.isatty(sys.stdout.fileno()):
            logging.info('stdin or stdout is not a tty, disabling capture')
            args._capture = False

        # reporting: we send command executions report to a web service; unless the report.enabled conf key is false
        from cligraphy.core.reporting import NoopReporter, ToolsPadReporter
        reporter = ToolsPadReporter(self) if (self.conf.report.enabled and args._reporting) else NoopReporter()
        reporter.report_command_start(sys.argv)

        decs = decorators.get_tags(args._func)
        logging.debug("Decorator tags: %s", decs)

        if decorators.Tag.interactive in decs or not args._capture:
            recorder = capture.NoopOutputRecorder()
        else:
            recorder = capture.BufferingOutputRecorder(max_output_size=self.conf.report.max_output_size)

        setproctitle('oc/parent/%s' % ' '.join(sys.argv[1:]))
        faulthandler.register(signal.SIGUSR2, all_threads=True, chain=False)  # pylint:disable=no-member

        if args._capture:
            # go ahead and run out command in a child process, recording all I/O
            logging.debug('Parent process %d ready to execute command process', os.getpid())
            status = capture.spawn_and_record(recorder, self._run_command_process, reporter.start, args)
            logging.debug('Command process exited with status %r', status)
        else:
            reporter.start()
            try:
                self._run_command_process(args)
            except SystemExit as exc:
                status = exc.code

        # report execution details
        reporter.report_command_exit(status)
        reporter.report_command_output(recorder.output_as_string())  # TODO(stefan): also report total output size
        reporter.stop()
        return status
