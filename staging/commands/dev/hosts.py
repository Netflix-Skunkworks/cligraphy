#!/usr/bin/env python
# Copyright 2013 Netflix

"""Manage /etc/hosts static entries for development
"""

import tempfile
import subprocess
import logging

MARKER = '# added by oc dev dns'


def configure(args):
    args.add_argument('-n', '--dry-run', action='store_true', help='dry run')
    args.add_argument('action', choices=['add', 'clear'], help='sub-command to run')
    args.add_argument('name_list', metavar='NAME', nargs='*', help='entry name')


def sudo_overwrite_file(filename, contents):
    """Overwrite file as root using sudo
    """
    with tempfile.NamedTemporaryFile() as tmpfp:
        tmpfp.write(contents)
        tmpfp.flush()
        subprocess.check_call('cat %s | sudo -p "Enter sudo password to overwite %s: " tee %s' % (tmpfp.name, filename, filename), shell=True)


def add_hosts_entries(args):
    """Add one or more static entries in /etc/hosts. Ignore existing names.
    """
    contents = open('/etc/hosts', 'r').read()

    filtered_name_list = []
    for name in args.name_list:
        if name in contents:
            logging.info('An entry for %s is already in /etc/hosts - skipping', name)
        else:
            filtered_name_list.append(name)

    if not filtered_name_list:
        logging.info('No names to add')
        return

    for name in filtered_name_list:
        contents = contents + '\n' + '127.0.0.1 %s %s' % (name, MARKER)

    contents += '\n'

    if args.dry_run:
        print contents
    else:
        sudo_overwrite_file('/etc/hosts', contents)


def reset_hosts_entries(args):
    """Add one or more static entries in /etc/hosts. Ignore existing names.
    """
    contents = open('/etc/hosts', 'r').readlines()
    filtered_lines = [ line.strip() for line in contents if MARKER not in line ]

    contents = '\n'.join(filtered_lines)

    if args.dry_run:
        print contents
    else:
        sudo_overwrite_file('/etc/hosts', contents)


def main(args):
    if args.action == 'add':
        add_hosts_entries(args)
    elif args.action == 'clear':
        reset_hosts_entries(args)
    else:
        raise Exception('Unknown action %s' % args.action)
