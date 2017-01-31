#!/usr/bin/env python
# Copyright 2014 Netflix

"""Configure oc git hooks on a repository"""

from nflx_oc.commands.dev.lint import find_git_root

import os
import logging

def configure(args):
    args.add_argument('-n', '--dry-run', action='store_true', help="don't actually do anything")
    args.add_argument('paths', metavar='path', nargs='*', help='paths of repositories to configure')

def get_oc_hooks_path():
    return os.path.join(os.getenv('OC_REPO_PATH'), 'setup', 'hooks')

def main(args):
    target_hooks_path = get_oc_hooks_path()
    if not os.path.isdir(target_hooks_path):
        logging.error("Could not find oc hooks under $OC_REPO_PATH (%s)", target_hooks_path)
        return 1

    paths = args.paths or (find_git_root('.'),)

    preflight = [hookup_repo(path, target_hooks_path, preflight=True) for path in paths]
    if not all(preflight):
        logging.error("Preflight failed")
        return 1

    if not args.dry_run:
        for path in paths:
            hookup_repo(path, target_hooks_path, preflight=False)


def hookup_repo(repo_path, target_hooks_path, preflight=True):
    """Replaces a git repo's .git/hooks folder by a symlink to the given target_hooks_path"""

    git_path = os.path.join(repo_path, '.git')
    repo_hooks_path = os.path.join(git_path, 'hooks')

    if not os.path.isdir(git_path):
        logging.error('[%s] is not a suitable git repository (no .git directory found)', repo_path)
        return False

    if os.path.islink(repo_hooks_path):
        link_dest = os.path.realpath(repo_hooks_path)
        if link_dest == target_hooks_path:
            logging.info('[%s] is already hooked to [%s]', repo_path, link_dest)
            return True
        else:
            logging.error('[%s] is hooked to [%s] (not [%s])', repo_path, link_dest, target_hooks_path)
            return False

    if not os.path.isdir(repo_hooks_path):
        logging.error('[%s] is not a suitable git repository (no .git/hooks directory found)', repo_path)
        return False

    if preflight:
        logging.info('Preflight OK for [%s] (%s->%s)', repo_path, repo_hooks_path, target_hooks_path)
    else:
        logging.info('Hooking up [%s] (%s->%s)', repo_path, repo_hooks_path, target_hooks_path)
        os.rename(repo_hooks_path, repo_hooks_path + '_pre_hookup')
        os.symlink(target_hooks_path, repo_hooks_path)

    return True
