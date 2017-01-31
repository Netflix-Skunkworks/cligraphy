#!/usr/bin/env python
# Copyright 2015, 2016 Netflix, Inc.

def prompt_int(prompt, value=None, default=None):
    """Prompt user for an int value"""
    while not isinstance(value, int):
        try:
            value = int(value)
        except TypeError:
            value = raw_input(prompt)
            if value == '':
                value = default
    return value


def prompt_enter_choice(prompt, values, exceptions=None):
    prompt = '%s (%s)? ' % (prompt, '/'.join(values))
    values = { value.upper(): value for value in values }
    while True:
        try:
            value = raw_input(prompt).upper()
        except BaseException as e:
            if exceptions and type(e) in exceptions:
                print
                return exceptions[type(e)]
            else:
                raise
        if value in values:
            return values[value]
