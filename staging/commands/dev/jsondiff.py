#!/usr/bin/env python
# Copyright 2014 Netflix

import requests

import sys
import json


def json_read(filename):
    if filename.startswith('http'):
        return requests.get(filename).json()
    else:
        with open(filename, 'r') as fp:
            return json.load(fp)


def print_diff(print_func, left, right):

    if left is not None and right is not None:

        if type(left) != type(right):
            print_func('Differing types: %r(%s) -> %r(%s)' % (left, type(left).__name__, right, type(right).__name__))
            return

    if type(left) == list:
        # right is also a list
        if not left:
            # right is also empty, no diffs
            return
        # non empty list, diff elements
        for index, (ileft, iright) in enumerate(zip(left, right)):
            print_diff(lambda x: print_func('Item %d: %s' % (index, x)), ileft, iright)

    elif type(left) == dict:
        leftkeys = set(left.keys())
        rightkeys = set(right.keys())

        for added in rightkeys - leftkeys:
            print_func('Added %s=%r' % (added, right[added]))

        for removed in leftkeys - rightkeys:
            print_func('Removed %s=%r' % (removed, left[removed]))

        for common in rightkeys.intersection(leftkeys):
            if left[common] != right[common]:
                print_diff(lambda x: print_func('Changed %s: %s' % (common, x)), left[common], right[common])

    else:
        print_func('Changed %r -> %r' % (left, right))


def configure(args):
    args.add_argument('left', metavar='FILENAME', help='left-side file')
    args.add_argument('right', metavar='FILENAME', help='right-side file')


def main(args):
    left = json_read(args.left)
    right = json_read(args.right)

    print_diff(lambda x: sys.stdout.write('%s\n' % x), left, right)
