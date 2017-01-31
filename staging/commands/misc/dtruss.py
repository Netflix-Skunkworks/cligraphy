#!/usr/bin/env python

"""dtruss a process without running it as root"""

import os
import time


def configure(args):
    args.add_argument('command', help='command line', nargs='+')


def main(args):
    os.system('sudo -p "Sudo password: " echo')
    pid = os.fork()
    if pid == 0:
        time.sleep(0.5)
        os.execlp(args.command[0], *args.command)
    else:
        os.system('sudo dtruss -f -p %d' % (pid))
