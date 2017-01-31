#!/usr/bin/env python
# Copyright 2015 Netflix, Inc.

"""Grab and export interesting information to help diagnose octools issues"""

from cligraphy.core import ctx, dictify_recursive

import getpass
import importlib
import json
import logging
import os
import os.path
import platform
import socket
import subprocess
import sys
import time
import traceback

import base64
import StringIO
import gzip


import requests


def _add_file_part(parts, name, filename):
    """Add a file to the diagnostics parts list, or an error message if the file could not be read"""
    try:
        with open(filename, 'r') as fp:
            parts.append((name, True, fp.read()))
    except:  # pylint:disable=bare-except
        parts.append((name, False, traceback.format_exc()))


def _add_output_part(parts, name, command, **kwargs):
    """Add the output of a command to the parts list, or an error message if the command failed"""
    try:
        parts.append((name, True, subprocess.check_output(command, stderr=subprocess.STDOUT, **kwargs)))
    except subprocess.CalledProcessError as cpe:
        parts.append((name, False, 'Command returned with status code %d. Output: [%s]' % (cpe.returncode, cpe.output)))
    except:  # pylint:disable=bare-except
        parts.append((name, False, traceback.format_exc()))


def _jsonify(value):
    """Stringify a value if it cannot be serialized to json, otherwise leave it alone"""
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


def _add_modinfo_part(parts, module_name):
    """Add information about a module to the parts list"""
    try:
        mod = importlib.import_module(module_name)
        details = {
            str(k): _jsonify(v) for k, v in mod.__dict__.items() if k not in ('__builtins__',)
        }
        parts.append(('modinfo:%s' % module_name, True, details))
    except:  # pylint:disable=bare-except
        parts.append(('modinfo:%s' % module_name, False, traceback.format_exc()))


def configure(parser):
    parser.add_argument("-n", "--dryrun", help="print generated diagnostics manifest, don't upload it", action="store_true")


def main(args):
    logging.info('Creating diagnostic manifest...')

    os.chdir('/tmp')
    diag = {}

    diag['user'] = getpass.getuser()
    diag['host'] = socket.gethostname()
    diag['ts'] = time.time()
    diag['python.version'] = tuple(sys.version_info)
    diag['platform'] = platform.platform()
    diag['environ'] = dict(os.environ)
    diag['conf'] = dictify_recursive(ctx.conf)

    parts = []
    diag['parts'] = parts


    _add_file_part(parts, 'requirements.txt',  os.path.join(ctx.conf.tool.repo_path, 'requirements.txt'))
    _add_output_part(parts, 'pip freeze', ['pip', 'freeze'])

    _add_modinfo_part(parts, 'requests')

    os.chdir(ctx.conf.tool.repo_path)
    _add_output_part(parts, 'git.branch', 'git rev-parse --abbrev-ref HEAD'.split())
    _add_output_part(parts, 'git.status', 'git status --porcelain'.split())
    _add_output_part(parts, 'git.version', 'git --version'.split())
    _add_output_part(parts, 'git.ls', 'ls -la .git'.split())

    _add_output_part(parts, 'uptime', ['uptime'])

    _add_output_part(parts, 'ssh.keys', ['ssh-add', '-l'])

    _add_output_part(parts, 'net.ifconfig', ['ifconfig'])
    _add_output_part(parts, 'net.routes', ['netstat', '-nr'])
    _add_file_part(parts, 'net.resolv.conf',  '/etc/resolv.conf')

    _add_output_part(parts, 'sys.ps', ['ps', 'aux'])
    _add_output_part(parts, 'sys.df', ['df', '-m'])
    _add_output_part(parts, 'sys.filevault', ['fdesetup', 'status'])

    _add_output_part(parts, 'net.ifconfig', ['ifconfig'])
    _add_output_part(parts, 'net.routes', ['netstat', '-nr'])
    _add_file_part(parts, 'net.resolv.conf',  '/etc/resolv.conf')

    _add_output_part(parts, 'sys.ps', ['ps', 'aux'])
    _add_output_part(parts, 'sys.df', ['df', '-m'])
    _add_output_part(parts, 'sys.filevault', ['fdesetup', 'status'])

    _add_file_part(parts, 'sys.usr_local_bin_pip',  '/usr/local/bin/pip')

    logging.info('Done creating diagnostic manifest')

    if args.dryrun or not ctx.conf.report.enabled:
        print json.dumps(diag, indent=4)
    else:
        buff = StringIO.StringIO()
        with gzip.GzipFile(fileobj=buff, mode="w", compresslevel=9) as fp:
            json.dump(diag, fp)
        body = base64.b64encode(buff.getvalue())

        logging.info('Uploading diagnostic manifest (body is %d bytes)', len(body))
        endpoint = '%s/api/v0.1/diagnostic' % ctx.conf.report.server
        response = requests.post(endpoint, data={
            'user_email': ctx.conf.user.email,
            'body': body,
            'stamp': int(time.time()),
        }, timeout=60)
        response.raise_for_status()
        logging.info('Diagnostic manifest posted successfully')
