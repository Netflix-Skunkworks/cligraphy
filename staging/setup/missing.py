#!/usr/bin/env python2.7

import sys


def read(fname):
    with open(fname, 'r') as fp:
        return set([ x.strip() for x in fp.readlines()])


def main():
    installed = read(sys.argv[1])
    wanted = read(sys.argv[2])
    todo = wanted - installed
    if not todo:
        return
    with open(sys.argv[3], 'w') as fp:
        fp.write("\n".join(todo))


if __name__ == '__main__':
    main()
