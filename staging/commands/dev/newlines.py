#!/usr/bin/env python
# Copyright 2014 Netflix

"""Append missing newlines to the end of source code files
"""


import os
import stat


SOURCE_CODE_EXTENSIONS = set(('py',))  # 'css','js','html',...


def walk(path):
    """Wraps os.walk"""
    result = []
    for root, _, filenames in os.walk(path):
        for name in filenames:
            result.append(os.path.join(root, name))
    return result


def get_last_byte(name):
    """Return the last byte in a file"""
    with open(name, 'r') as infp:
        infp.seek(-1, 2)
        return infp.read(1)


def configure(args):
    args.add_argument('-n', '--dry-run', action='store_true', help='dry run')
    args.add_argument('name_list', metavar='NAME', nargs='+', help='file or directory name')


def main(args):
    files = []
    for name in args.name_list:
        name = os.path.abspath(name)
        fstat = os.stat(name)
        if stat.S_ISDIR(fstat.st_mode):
            files.extend(walk(name))
        else:
            files.append(name)

    source_code_files = [ name for name in files if name.rpartition('.')[-1] in SOURCE_CODE_EXTENSIONS ]
    missing_last_newline = [ name for name in source_code_files if get_last_byte(name) != '\n' ]

    if args.dry_run:
        print 'Missing newlines at the end of %d files:' % len(missing_last_newline)
        for name in missing_last_newline:
            print ' ', name
    else:
        for name in missing_last_newline:
            if os.access(name, os.W_OK):
                print 'Fixing', name
                with open(name, 'a') as fpout:
                    fpout.write('\n')
