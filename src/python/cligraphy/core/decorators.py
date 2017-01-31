#!/usr/bin/env python
# Copyright 2013 Netflix, Inc.

"""Decorators."""

import cligraphy.core.parsers
from cligraphy.core.util import undecorate_func

from functools import wraps
import logging

from enum import Enum


class Tag(Enum):
    """Enumeration of the decorator tags we support."""
    beta = 1
    disabled = 2
    strict = 3
    interactive = 4


class DisabledCommandException(Exception):
    """Raised when a @disabled command is invoked."""
    pass


def tag(tag_enum, reason='No reason given'):
    """Decorator that disables a command."""
    # pylint:disable=missing-docstring,unused-argument
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func(*args, **kwargs)
        wrapper.tag = tag_enum
        wrapper.original_func = func
        return wrapper
    return actual_decorator


def disabled(reason='No reason given'):
    """Decorator that disables a command."""
    # pylint:disable=missing-docstring,unused-argument
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raise DisabledCommandException('This command is disabled: %s' % reason)
        wrapper.tag = Tag.disabled
        wrapper.original_func = func
        return wrapper
    return actual_decorator


def beta(reason='No reason given'):
    """Decorator for unstable commands - user will be prompted to confirm before execution."""
    # pylint:disable=missing-docstring,unused-argument
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = 'WARNING - this command is marked as beta: %s - are you sure you want to continue (y/N)? ' % reason
            logging.warning(message)
            confirm = raw_input(message)
            if confirm and confirm.lower() in ('y', 'yes'):
                func(*args, **kwargs)
            else:
                print 'Cancelled'
        wrapper.tag = Tag.beta
        wrapper.original_func = func
        return wrapper
    return actual_decorator


def strict(reason='No reason given'):
    """Command decorator that disables fuzzy matching."""
    # pylint:disable=missing-docstring,unused-argument
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if cligraphy.core.parsers.FUZZY_PARSED:
                logging.error('This command must be called by its exact name (%s). Please run as %s',
                              reason, cligraphy.core.parsers.FUZZY_PARSED[0][-1])
                return
            else:
                func(*args, **kwargs)
        wrapper.tag = Tag.strict
        wrapper.original_func = func
        return wrapper
    return actual_decorator


def get_tags(decorated_func):
    """Return the set of decorator tags applied to decorated_func."""
    _, decorators = undecorate_func(decorated_func)
    return set([ x.tag for x in decorators ])
