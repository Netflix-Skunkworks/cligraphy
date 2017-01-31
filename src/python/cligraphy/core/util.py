#!/usr/bin/env python
# Copyright 2013 Netflix, Inc.

"""Utility classes
"""

from contextlib import contextmanager
import logging
import signal
import sys


class TimeoutError(Exception):
    """Timeout Error"""
    pass


@contextmanager
def timeout(seconds,  error_message='Timeout'):
    """Timeout context manager using SIGALARM."""
    def _handle_timeout(signum, frame):  # pylint:disable=unused-argument,missing-docstring
        raise TimeoutError(error_message)
    if seconds > 0:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(seconds)
    try:
        yield
    finally:
        if seconds > 0:
            signal.alarm(0)


def undecorate_func(func, decorators=None):
    """Finc the actual func behind any number of decorators
    """
    if decorators is None:
        decorators = []
    if hasattr(func, 'original_func'):
        decorators.append(func)
        return undecorate_func(getattr(func, 'original_func'), decorators)
    else:
        return func, decorators


def try_import(module_name):
    """Attempt to import the given module (by name), returning a tuple (True, module object) or (False,None) on ImportError"""
    try:
        module = __import__(module_name)
        return True, module
    except ImportError:
        return False, None


def call_chain(chain, *args, **kwargs):
    if len(chain) == 1:
        return chain[0](*args, **kwargs)
    elif len(chain) == 2:
        return chain[1](lambda: chain[0](*args, **kwargs))
    elif len(chain) == 3:
        return chain[2](lambda: chain[1](lambda: chain[0](*args, **kwargs)))
    else:
        raise Exception("call_chain is a hack and doesn't support chains longer than 3")


def profiling_wrapper(func):
    import cProfile, StringIO, pstats
    pr = cProfile.Profile()
    pr.enable()
    try:
        func()
    finally:
        pr.disable()
        s = StringIO.StringIO()
        sortby = 'cumulative'
        ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print s.getvalue()


def pdb_wrapper(func):
    try:
        return func()
    except Exception:
        import pdb
        import traceback
        etype, value, tb = sys.exc_info()
        logging.info('Top level exception caught, entering debugger')
        traceback.print_exc()
        pdb.post_mortem(tb)
        raise
