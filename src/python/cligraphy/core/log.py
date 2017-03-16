#!/usr/bin/env python
# Copyright 2013, 2014 Netflix, Inc.

"""Command line tools entry point"""

from cligraphy.core.util import try_import

from remember import memoize

import json
import logging
import logging.config
import os
import sys


#  new log level for, you guessed it, dryrun logging.
#  See: http://stackoverflow.com/a/13638084
DRYRUN_num = 15
DRYRUN_name = 'DRYRUN'


def _dryrun(self, message, *args, **kws):
    if self.isEnabledFor(DRYRUN_num):
        self._log(DRYRUN_num, message, args, **kws)


class JsonHandler(logging.Handler):

    def __init__(self, destination, *args, **kwargs):
        self.destination = destination
        self.recurse = False
        super(JsonHandler, self).__init__(*args, **kwargs)

    def emit(self, record):
        if self.recurse:
            return
        try:
            self.recurse = True
            self._emit(record)
        finally:
            self.recurse = False

    def _emit(self, record, first_attempt=True):
        try:
            msg = record.msg % record.args
        except TypeError:
            msg = str(record.msg) + ' (formatting error)'

        output = {}
        try:
            output = {
                'ts': int(record.created * 1000),
                'level': record.levelno,
                'msg': msg,

                # module, function, ...
                'module': record.module,
                'file': record.filename,
                'func': record.funcName,
                'line': record.lineno,

                # process and thread information
                'tid': record.thread,
                'tname': record.threadName,
                'pid': record.process,
                'pname': record.processName,
            }

            if hasattr(record, 'extra'):
                if first_attempt:
                    output['extra'] = record.extra
                else:
                    output['extra'] = {'_omitted': True}  # We tried to serialize our record once and got an error, so omit ctx now

            if record.exc_info and record.exc_info[0] and record.exc_info[1]:
                output['exc_type'] = record.exc_info[0].__name__
                output['exc_msg'] = repr(record.exc_info[1].message)
                tb = []
                cur = record.exc_info[2]
                while cur:
                    frame = cur.tb_frame
                    tb.append((frame.f_code.co_filename, frame.f_code.co_name, frame.f_lineno))
                    cur = cur.tb_next
                output['exc_tb'] = tb

            try:
                msg = json.dumps(output)
                self.destination.log_event('log', record.created, msg)
            except (TypeError, OverflowError):
                if first_attempt:
                    return self.emit(record, False)  # Try again, without ctx this time
                else:
                    raise

        except (KeyboardInterrupt, SystemExit):
            raise
        except:  # pylint:disable=bare-except
            print 'log.structured: serialization error - details follow'
            print(output)
            self.handleError(record)


def silence_verbose_loggers():
    logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)


@memoize.memoize()
def _get_dict_config():
    dict_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'datefmt': '%Y-%m-%d %H:%M:%S',
                'format': "%(asctime)s %(levelname)-8s %(module)s %(funcName)s %(message)s"
            },
        },
        'handlers': {
            'defaultHandler': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'default'
            },
        },
        'loggers': {
            '': {
                'handlers': (['defaultHandler']),
                'level': 'WARN',
            },
        }
    }

    if os.isatty(sys.stderr.fileno()) and try_import('colorlog')[0]:
        import colorlog
        colorlog.default_log_colors.update({DRYRUN_name: 'blue'})
        dict_config['formatters']['colors'] = {
            '()': 'colorlog.ColoredFormatter',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': "%(log_color)s%(asctime)s %(levelname)-8s%(reset)s %(purple)s%(module)s/%(funcName)s%(reset)s %(message)s"
        }
        dict_config['handlers']['defaultHandler']['formatter'] = 'colors'

    return dict_config


def setup_logging(level=None):
    """Configure logging"""
    logging.addLevelName(DRYRUN_num, DRYRUN_name)
    logging.Logger.dryrun = _dryrun
    try:
        logging.config.dictConfig(_get_dict_config())
        logging.captureWarnings(True)
        silence_verbose_loggers()
        if level is not None:
            logging.getLogger().setLevel(level)
    except Exception:  # pylint:disable=broad-except
        logging.basicConfig(level=logging.WARN)
        logging.warn('Could not configure logging, using basicConfig', exc_info=True)
