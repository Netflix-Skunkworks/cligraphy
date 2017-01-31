#!/usr/bin/env python
# Copyright 2013 Netflix


"""Lint your code!
Pylint wrapper
"""

import stat
import os
import re
import logging
import subprocess
import sys

IGNORE = r'^(\..*|.*egg-info|dist|build|testdata)$'


def _find_all_python_modules(path, ignore_re, results):
    """Find all folders under (and including) path that contain an __init__.py file"""
    logging.debug('visiting %s', path)
    dirs = []
    for name in os.listdir(path):
        if ignore_re.match(name):
            logging.debug('ignored %s', name)
            continue
        if stat.S_ISDIR(os.stat(os.path.join(path, name)).st_mode):
            dirs.append(name)
        elif name == '__init__.py':
            results.add(path)
    for dirname in dirs:
        _find_all_python_modules(os.path.join(path, dirname), ignore_re, results)


def find_python_modules(path):
    """Find unique python modules, grouping hierarchies"""
    ignore_re = re.compile(IGNORE)
    results = set()
    _find_all_python_modules(path, ignore_re, results)
    kept = set()
    for path in results:
        prefix = path.rpartition('/')[0]
        if prefix not in results:
            kept.add(path)
    return sorted(list(kept))


def find_git_root(path):
    """Find the first git root in path and its parents"""
    if os.path.exists(os.path.join(path, '.git')):
        return path
    if not path or path == '/':
        return None
    return find_git_root(os.path.abspath(os.path.join(path, '..')))


def normalize_path(path):
    """Normalize paths - as of now only transforms . into ../$CWD"""
    if path == '.':
        return os.path.join('..', os.getcwd().split('/')[-1])
    else:
        return path


def interact(lines, editor='subl'):
    """Sublime mode: show lint violations one by one, opening sublime at the proper location, and waiting for enter between lines"""
    print '--- Press enter to show the next error. Note that line offsets will diverge as you add/remove lines from the code -- '
    for line in lines:
        if line.startswith('/') and ':' in line:
            print line
            os.system('%s %s' % (editor, line.split(' ')[0]))
            sys.stdin.readline()


def configure(args):
    args.add_argument('-g', '--git-root', action='store_true', help='lint from git repository root')
    args.add_argument('-n', '--dry-run', action='store_true', help='show paths that would be linted')
    args.add_argument('-i', '--interactive', action='store_true', help='iterate over issues, opening sublime at the right location')
    args.add_argument('-e', '--errors-only', action='store_true', help='show errors only')
    args.add_argument('paths', metavar='path', nargs='*', help='paths to lint')


def main(args):
    lines = []

    git_root = find_git_root('.')

    if args.git_root:
        path = git_root
        if not path:
            print 'no git root found'
            return 1
    else:
        path = '.'
    paths = args.paths if args.paths else find_python_modules(path)
    for path in paths:
        if args.dry_run:
            print path
            continue
        path = normalize_path(path)

        pylintrc = '.pylintrc'
        if not os.path.exists(pylintrc):
            if git_root:
                pylintrc = os.path.join(git_root, pylintrc)
            if not os.path.exists(pylintrc):
                pylintrc = '%s/conf/pylintrc' % os.getenv('OC_REPO_PATH')

        #FIXME(stf/oss) venv name
        command = '${OC_PYTHON_ENV_ROOT}/octools-cligraphy/bin/pylint --rcfile %s %s %s' % (pylintrc, '--errors-only' if args.errors_only else '', path)
        logging.debug('Linting %s with %s', path, command)
        try:
            subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError, cpe:
            lines.extend(cpe.output.split('\n'))

    if lines:
        if args.interactive:
            interact(lines)
        else:
            print '\n'.join(lines)
            print 'Issues were found'
        sys.exit(1)
