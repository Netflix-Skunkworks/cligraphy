#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Unix terminal utils
"""

import fcntl
import termios
import struct
import sys
import os


def _ioctl_get_window_size(fd):
    """Calls TIOCGWINSZ for the given fd
    """
    try:
        return struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
    except IOError:
        return


def get_terminal_size():
    """Get current terminal size (best effort)
    """
    cr = _ioctl_get_window_size(0) or _ioctl_get_window_size(1) or _ioctl_get_window_size(2)
    if not cr:
        with os.open(os.ctermid(), os.O_RDONLY) as fd:
            cr = _ioctl_get_window_size(fd)
    return int(cr[0]), int(cr[1])


def set_terminal_size(lines, columns):
    """Set current terminal size
    """
    winsize = struct.pack("HHHH", lines, columns, 0, 0)
    fcntl.ioctl(1, termios.TIOCSWINSZ, winsize)
    sys.stdout.write("\x1b[8;{lines};{columns}t".format(lines=lines, columns=columns))
