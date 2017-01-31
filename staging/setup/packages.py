#!/usr/bin/env python

import yaml
import sys
import platform


def select(packages, os):
    for pack, overrides in packages.iteritems():
        selection = overrides.get(os, pack) if overrides else pack
        if not isinstance(selection, basestring):
            for item in selection:
                print item
        else:
            print selection


def main():
    os = platform.system().lower()

    if os == 'linux':
        os = platform.dist()[0].lower()

    packages = yaml.load(open(sys.argv[1]))
    select(packages['all'], os)
    select(packages.get(os, {}), os)


if __name__ == '__main__':
    main()
