#!/usr/bin/env python
# Copyright 2014 Netflix

"""Precompile python modules"""

from nflx_oc.commands.dev.lint import find_git_root, find_python_modules, normalize_path

import compileall
import logging
import subprocess
import os.path


def clean_and_compile(path):
    path = os.path.abspath(normalize_path(path))

    logging.debug('Cleaning %s', path)
    command = "find %s -name '*.pyc' -delete -o -name '*.pyo' -delete" % path
    try:
        subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError, cpe:
        logging.exception('Exception while cleaning %s' % path)

    logging.debug('Compiling %s', path)
    command = "python -O -m compileall -q %s" % path
    try:
        subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError, cpe:
        logging.error('Exception while compiling %s. Output follows:\n%s', path, cpe.output)


def configure(args):
    args.add_argument('-g', '--git-root', action='store_true', help='precompile from git repository root')
    args.add_argument('-n', '--dry-run', action='store_true', help='show paths that would be precompile')
    args.add_argument('paths', metavar='path', nargs='*', help='paths to precompile')


def main(args):
    if args.git_root:
        path = find_git_root('.')
        if not path:
            print 'no git root found'
            return 1
    else:
        path = '.'

    paths = args.paths if args.paths else find_python_modules(path)
    for path in paths:
        if args.dry_run:
            continue

        clean_and_compile(path)
