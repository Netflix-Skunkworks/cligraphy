#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Session recording and replay
"""

from cligraphy.core import capture
from cligraphy.core.capture.termsize import get_terminal_size, set_terminal_size

import os.path
import os
import time


LOG_ROOT = '/tmp/session'


def session_capnp():
    """Load out capnproto schema
    """
    import capnp
    capnp.remove_import_hook()
    return capnp.load(os.path.join(capture.__path__[0], 'session.capnp'))


class CapnpSessionRecorder(capture.Recorder):
    """Records a pty session
    """

    def __init__(self):
        self.last_ts = time.time()
        self.out_fp = None
        self.session_capnp = session_capnp()
        tm = time.gmtime()
        dirname = '%s/%04d/%02d/%02d/%02d' % (LOG_ROOT, tm.tm_year, tm.tm_mon, tm.tm_mday, tm.tm_hour)
        try:
            umask = os.umask(2)
            os.makedirs(dirname)
            os.umask(umask)
        except OSError:
            pass
        self.filename = dirname + '/%s-%d.log' % (os.getenv('USER'), time.time() * 1000)

    def start(self):
        """Start a session record
        """
        self.out_fp = open(self.filename, 'wb')

        session = self.session_capnp.Session.new_message()

        session.username = os.getenv('USER')
        session.timestamp = int(time.time() * 1000)

        window_size = session.init('windowSize')
        window_size.lines, window_size.columns = get_terminal_size()

        environ = os.environ.items()
        session_env = session.init('environment', len(environ))
        for index, item in enumerate(environ):
            session_env[index].name = item[0]
            session_env[index].value = item[1]

        session.write(self.out_fp)
        self.out_fp.flush()
        self.last_ts = time.time()

    def _timecode(self):
        """Returns the current time code
        """
        now = time.time()
        ret = max(now - self.last_ts, 0.0)
        self.last_ts = now
        return ret

    def end(self, exitcode=0):
        """Finish a session record
        """
        event = self.session_capnp.Event.new_message()
        event.timecode = self._timecode()
        event.type = 'sessionEnd'
        event.status = exitcode
        event.write_packed(self.out_fp)
        self.out_fp.close()

    def record_window_resize(self, lines, columns):
        """Record a window resizing event
        """
        event = self.session_capnp.Event.new_message()
        event.timecode = self._timecode()
        event.type = 'windowResized'
        window_size = event.init('windowSize')
        window_size.lines, window_size.columns = lines, columns
        event.write_packed(self.out_fp)

    def record_user_input(self, data):
        """record user input separately from terminal output
        """
        event = self.session_capnp.Event.new_message()
        event.timecode = self._timecode()
        event.type = 'userInput'
        event.data = data
        event.write_packed(self.out_fp)

    def record_server_output(self, data):
        """record terminal output (user + server originated)
        """
        event = self.session_capnp.Event.new_message()
        event.timecode = self._timecode()
        event.type = 'ptyInput'
        event.data = data
        event.write_packed(self.out_fp)


class CapnpSessionPlayer(capture.Player):
    """Plays a recorded session
    """

    def __init__(self, filename):
        self.filename = filename
        self.session_capnp = session_capnp()
        self.fpin = open(self.filename, 'rb')
        self.session = self.session_capnp.Session.read(self.fpin)

    def close(self):
        """Close this player
        """
        self.fpin.close()

    def play(self):
        """Generator of session playback events - basically (timecode, data) tuples
        """
        set_terminal_size(self.session.windowSize.lines, self.session.windowSize.columns)

        skipped = 0
        for event in self.session_capnp.Event.read_multiple_packed(self.fpin):
            if event.type == 'ptyInput':
                yield event.timecode + skipped, event.data
                skipped = 0
            elif event.type == 'windowResized':
                set_terminal_size(event.windowSize.lines, event.windowSize.columns)
                yield event.timecode + skipped, None
                skipped = 0
            else:
                skipped += event.timecode
        self.close()
