#!/usr/bin/env python
# Copyright 2014 Netflix

"""Refresh oc tools install

refresh updates your oc tools install:
- runs "git pull" on your octools repository
- installs/reinstalls/upgrades python dependencies
- precompiles python files
- refreshes commands cache

Quick mode disables most of this and only refreshes the commands cache.
"""

import subprocess
import os
import sys
import random
import urlparse

from pip.req.req_install import parse_editable
from pip.utils import get_installed_distributions

from cligraphy.core.parsers import NO_HELP
from cligraphy.core import ctx

from nflx_oc.commands.dev.pycompile import clean_and_compile
from nflx_oc.commands.dev.hookup import get_oc_hooks_path, hookup_repo


TIPS = [
    "You can disable these random tips: oc conf add -t bool refresh.tips false"
]


def _build_tips(command_maps):
    def _explore(command_map, path):
        for name, node in command_map.iteritems():
            if node.get('type') == 'cmd':
                full_name = ' '.join(path + (name,))
                node_help = node.get('help')
                if node_help not in (None, NO_HELP) and len(node_help) > 1:
                    TIPS.append('%s: %s' % (full_name, node_help))
                else:
                    TIPS.append('Looks like "%s" is missing a help string... You could help out by adding it!' % (full_name))
            else:
                _explore(node, path + (name,))
    for namespace, command_map in command_maps:
        _explore(command_map['commands'], filter(None, ('oc', namespace,)))


def _install_deps(venv_prefix, filename):
    """"""
    reqs = []
    installed_locations = { x.key: x.location for x in get_installed_distributions() }
    with open(filename, 'r') as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('-i '):
                continue
            if line.startswith('-e'):
                # skip req if we have a local copy
                editable = parse_editable(line[3:])
                req_name = editable[0]
                url = editable[1]
                path = urlparse.urlsplit(url).path
                repo_name = path.rpartition('/')[-1]
                if repo_name.endswith('.git'):
                    repo_name = repo_name[:-4]
                local_checkout_path = os.path.join(ctx.conf.repos.root, repo_name)
                if os.path.exists(local_checkout_path):
                    # we have a local checkout, check that it's what we use in our venv
                    installed_location = installed_locations.get(req_name)
                    if local_checkout_path == installed_location:
                        print '[refresh] info: using local checkout %s for %s' % (local_checkout_path, req_name)
                        continue
                    else:
                        if installed_location is not None:
                            print '[refresh] notice: local checkout of %s exists in %s but another install is active in octools (%s)' % (req_name, local_checkout_path, installed_location)
            reqs.append(line)

    final_req_fname = os.path.join(ctx.conf.user.dotdir, 'requirements.txt')  # FIXME(stf/oss)
    with open(final_req_fname, 'w') as fp:
        fp.write('\n'.join(reqs))

    command_line = [
        os.path.join(venv_prefix, 'pip'),
        'install',
        '-r', final_req_fname
    ]
    env = { 'PIP_EXISTS_ACTION': 's' }
    env.update(os.environ)
    try:
        subprocess.check_output(command_line, env=env, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as cpe:
        print "[refresh] %s failed:" % (' '.join(command_line))
        print cpe.output
        raise


def _check_for_issues():
    # git vulnerabilities before 2.7.4
    try:
        git_version = subprocess.check_output(['git', '--version']).strip()
        git_version_int = int(''.join(git_version.rpartition(' ')[-1].split('.')[0:3]))
        if git_version_int < 274:
            print '[refresh] git versions under 2.7.4 are vulnerable - upgrade now! (on osx, brew update && brew upgrade git)'
    except:
        pass


def refresh(cligraph, quick):
    oldcwd = os.getcwd()
    try:
        os.chdir(os.getenv('OC_REPO_PATH'))

        _check_for_issues()

        if not os.access('.', os.W_OK):
            print '[refresh] repository is not writeable (shared install?), forcing quick mode'
            quick = True

        if not quick:
            print '[refresh] refreshing repository...'
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD']).strip()
            subprocess.check_output(['git', 'pull', 'origin', branch])

            venv = os.getenv('VIRTUAL_ENV')
            if venv:
                venv_prefix = os.path.dirname(sys.executable)
                print '[refresh] refreshing python dependencies...'
                _install_deps(venv_prefix, 'requirements.txt')
                subprocess.check_output((os.path.join(venv_prefix, 'python') + ' setup.py develop --no-deps').split(' '))
            else:
                print '[refresh] $VIRTUAL_ENV is not defined, not refreshing python dependencies.'

            print '[refresh] precompiling python files...'
            clean_and_compile('.')

            print '[refresh] hooking up your repo...'
            hookup_repo(os.getenv('OC_REPO_PATH'), get_oc_hooks_path(), preflight=False)

        print '[refresh] refreshing commands cache...'
        command_maps = cligraph.get_command_maps(autodiscover=True)
        _build_tips(command_maps)
    finally:
        os.chdir(oldcwd)

    if ctx.conf.refresh.tips:
        print 'Random tip:\n    %s' % (random.choice(TIPS))


def configure(parser):
    parser.add_argument('-q', '--quick', help="Quick mode: only refresh commands cache, don't refresh repository or dependencies",
                        action='store_const', default=False, const=True)


def main(args):
    refresh(ctx.cligraph, args.quick)
