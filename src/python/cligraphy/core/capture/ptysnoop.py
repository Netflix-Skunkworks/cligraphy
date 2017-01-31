#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Capture interactive unix terminal activity

Basically a python reimplementation of ye old 'script' utility
"""

import errno
import fcntl
import logging
import os
import select
import signal
import struct
import termios
import threading
import multiprocessing
import time

STDIN, STDOUT, STDERR = 0, 1, 2
DEFAULT_BUFF_SIZE = 128
WAKEUP = '!'


def xwrite(fileno, data):
    """Write data to fileno
    """
    offset = 0
    remaining = len(data)
    while remaining > 0:
        count = os.write(fileno, data[offset:])
        remaining -= count
        offset += count


class Script(object):
    """A python reimplementation of the script utility
    """

    def __init__(self, recorder, buff_size=DEFAULT_BUFF_SIZE, idle_timeout=0, select_timeout=1):
        self.recorder = recorder
        self.buff_size = buff_size
        self.idle_timeout = idle_timeout
        self.select_timeout = select_timeout
        self.activity_stamp = time.time()
        self.master = None
        self.slave = None
        self.child_pid = None
        self.start_event = multiprocessing.Event()
        self.stop_event = threading.Event()
        self.resize_event = threading.Event()
        self.tcattr = None
        self.wakeup_r, self.wakeup_w = os.pipe()

    def _on_stdin_input(self):
        """User typing something
        """
        data = os.read(STDIN, self.buff_size)

        if len(data) == 0:  # EOF
            self.stop_event.set()
        else:
            xwrite(self.master, data)
            self.recorder.record_user_input(data)

    def _on_pty_input(self):
        """Some data has been displayed on screen
        """
        data = os.read(self.master, self.buff_size)

        if len(data) == 0:
            self.stop_event.set()
        else:
            xwrite(1, data)
            self.recorder.record_server_output(data)

    def _on_wakeup(self):
        """Our main thread woke us up
        """
        os.read(self.wakeup_r, 1)

        if self.resize_event.is_set():
            self.resize_event.clear()
            data = fcntl.ioctl(STDIN, termios.TIOCGWINSZ, '0123')
            lines, columns = struct.unpack('hh', data)
            self.recorder.record_window_resize(lines, columns)
            fcntl.ioctl(self.slave, termios.TIOCSWINSZ, data)

    def _io_loop(self):
        """I/O loop (executed as a parent process thread)
        """

        self.start_event.set()

        io_actions = {
            STDIN: self._on_stdin_input,
            self.master: self._on_pty_input,
            self.wakeup_r: self._on_wakeup,
        }

        rlist = io_actions.keys()

        self.recorder.start()

        while not self.stop_event.is_set():
            try:
                activity = select.select(rlist, [], [], self.select_timeout)[0]
            except select.error as err:
                assert err.args[0] != errno.EINTR, 'Should not be getting interrupted syscalls in thread'
                raise

            if activity:
                self.activity_stamp = time.time()
            elif self.idle_timeout > 0:
                if time.time() > self.activity_stamp + self.idle_timeout:
                    self.stop_event.set()

            for active_fd in activity:
                try:
                    io_actions[active_fd]()
                except OSError as ose:
                    assert ose.errno != errno.EINTR, 'Should not be getting interrupted syscalls in thread'
                    raise

    def _on_sigchild(self, *args, **kwargs):  # pylint:disable=unused-argument
        """SIGCHILD handler
        """
        signal.signal(signal.SIGCHLD, self._on_sigchild)
        # logging.debug('Got sigchild')
        self.stop_event.set()
        os.write(self.wakeup_w, WAKEUP)

    def _on_sigwinch(self, *args, **kwargs):  # pylint:disable=unused-argument
        """SIGWINCH handler
        """
        # logging.debug('Got sigwinch')
        self.resize_event.set()
        os.write(self.wakeup_w, WAKEUP)

    def _run_parent(self):
        """Parent process main loop
        """
        io_thread = threading.Thread(group=None, target=self._io_loop, name='ptysnoop_io_thread')
        io_thread.start()

        signal.signal(signal.SIGCHLD, self._on_sigchild)
        signal.signal(signal.SIGWINCH, self._on_sigwinch)

        while not self.stop_event.is_set():
            self.stop_event.wait(10)

        io_thread.join()

    def _open_pty(self):
        """Create a PTY
        """
        # get our terminal params
        self.tcattr = termios.tcgetattr(STDIN)
        winsize = fcntl.ioctl(STDIN, termios.TIOCGWINSZ, '0123')
        # open a pty
        self.master, self.slave = os.openpty()
        # set the slave's terminal params
        termios.tcsetattr(self.slave, termios.TCSANOW, self.tcattr)
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, winsize)

    def _setup_slave_pty(self):
        """Set suitable tty options for our pty slave
        """
        os.setsid()
        fcntl.ioctl(self.slave, termios.TIOCSCTTY, 0)
        os.close(self.master)
        os.dup2(self.slave, STDIN)
        os.dup2(self.slave, STDOUT)
        os.dup2(self.slave, STDERR)  # FIXME can we handle stderr better?
        os.close(self.slave)

    def _fix_tty(self):
        """Set suitable tty options
        """
        assert self.tcattr is not None
        iflag, oflag, cflag, lflag, ispeed, ospeed, chars = self.tcattr  # pylint:disable=unpacking-non-sequence
        # equivalent to cfmakeraw
        iflag &= ~(termios.IGNBRK | termios.BRKINT | termios.PARMRK | termios.ISTRIP | termios.INLCR |
                   termios.IGNCR | termios.ICRNL | termios.IXON)
        oflag &= ~termios.OPOST
        lflag &= ~(termios.ECHO | termios.ECHONL | termios.ICANON | termios.ISIG | termios.IEXTEN)
        cflag &= ~(termios.CSIZE | termios.PARENB)
        cflag |= termios.CS8
        termios.tcsetattr(STDIN, termios.TCSANOW, [iflag, oflag, cflag, lflag, ispeed, ospeed, chars])

    def _done(self):
        """Nicely close our logs, reset the terminal and exit
        """
        os.close(self.master)
        termios.tcsetattr(STDIN, termios.TCSADRAIN, self.tcattr)

        pid, status = os.waitpid(self.child_pid, os.WNOHANG)
        if pid != 0:
            assert pid == self.child_pid
            exit_code = status >> 8
            self.recorder.end(exit_code)
            return exit_code
        else:
            logging.warn('waitpid(%d) returned %d %d', self.child_pid, pid, status)

    def run(self, callback, parent_callback, *args, **kwargs):
        """Setup, fork and run
        """

        if threading.active_count() > 1:
            threads = threading.enumerate()
            logging.warning('Programming error: there are %d active threads (list follows)', len(threads))
            for thread in threads:
                logging.warning('  - %s', thread)
            logging.warning('Creating threads before forking can lead to issues and should be avoided')

        self._open_pty()
        self._fix_tty()

        pid = os.fork()
        if pid == 0:
            # child
            self._setup_slave_pty()
            self.start_event.wait()
            callback(*args, **kwargs)
        else:
            # parent
            try:
                self.child_pid = pid
                if parent_callback:
                    parent_callback()
                self._run_parent()
            finally:
                return self._done()
