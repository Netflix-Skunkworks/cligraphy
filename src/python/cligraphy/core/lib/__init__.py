#!/usr/bin/env python
# Copyright 2015, 2016 Netflix, Inc.

import logging
import time
import os.path

from decorator import decorator
from pathlib import Path


def retry(retry_count, exceptions, log_message, retry_sleep=0, backoff=1, maxdelay=None):
    """ Decorator to implement retry logic
        :retry_count int: number of attempts before aborting on failure.
        :exceptions tuple: exception classes to trap and retry on.
        :retry_sleep float or int: sets the initial delay between attempts in seconds.
        :backoff  float or int: sets the factor by which the delay should lengthen after each failure.
                                backoff must be greater than 1, or else it isn't really a backoff.
        :maxdelay int: exponential backoffs can get pretty lengthy. This limits the maximum delay

    """
    @decorator
    def _retry(f, *args, **kwargs):
        _tries, _delay = retry_count, retry_sleep
        while _tries > 0:
            try:
                return f(*args, **kwargs)
            except (exceptions) as e:
                logging.debug('Failed to %s. Attempt: %s/%s', log_message, retry_count + 1 - _tries, retry_count)
                _tries -= 1
                if _tries == 0:
                    logging.error('Failed to %s with %s attempts', log_message, retry_count)
                    raise(e)
                time.sleep(_delay)
                _delay *= backoff
                if maxdelay and _delay > maxdelay:
                    _delay = maxdelay
    return _retry


def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


def is_file(parser, item):
    """
    Takes an argparse.ArgumentParser instance and value that you want
    validated.  If it is a file, returns a resolved pathlib.PosixPath object.
    If it isn't, prints the appropriate error and aborts execution via the
    ArguementParser.

    :param parser: ArgumentParser that you are trying to validate the item from
    :type parser: argparse.ArgumentParser
    :param item: path to file to test if is a file
    :type item: str
    :return: resolved Path object
    :rtype: pathlib.PosixPath
    """
    f = Path(os.path.expanduser(item))
    try:
        f = f.resolve()
    except IOError:
        parser.error('The file {file!r} does not exist'.format(file=item))
    if not f.is_file():
        parser.error('{item!r} is not a file'.format(item=item))
    try:
        with f.open('r') as fp:
            pass
    except IOError as e:
        parser.error('{item!r} cannot be opened for reading: {err!s}'.format(
            item=item, err=e
        ))
    return f

def get_user_choice(prompt, choices, case_lower=True):
    """ prompt user to make a choice. converts choices to lowercase unicode strings
        prompt: str:
        choices: list of str or int:
        case_lower: defaults to True for lower case enforcement
        return: unicode choice
    """
    if case_lower:
        _vals = [unicode(x).lower() for x in choices]
    else:
        _vals = [unicode(x) for x in choices]
    while True:
        if case_lower:
            _input = unicode(raw_input(prompt)).lower()
        else:
            _input = unicode(raw_input(prompt))
        if _input in _vals:
            return _input
