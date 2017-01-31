#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

"""Terminal session capture"""

from cligraphy.core.capture import ptysnoop

from abc import abstractmethod


class Recorder(object):

    def start(self):
        pass

    def end(self, exitcode=0):
        """Finish a session record
        """

    def record_window_resize(self, lines, columns):
        """Record a window resizing event
        """

    @abstractmethod
    def record_user_input(self, data):
        """record user input separately from terminal output
        """

    @abstractmethod
    def record_server_output(self, data):
        """record terminal output (user + server originated)
        """


class Player(object):
    """Plays a recorded session
    """

    @abstractmethod
    def close(self):
        """Close this player
        """

    @abstractmethod
    def play(self):
        """Generator of session playback events - basically (timecode, data) tuples
        """


class NoopOutputRecorder(Recorder):

    def output_as_string(self):
        return '(output discarded)'


class BufferingOutputRecorder(Recorder):
    """Recorder that buffers output up to a maximum size"""

    def __init__(self, max_output_size):
        super(BufferingOutputRecorder, self).__init__()
        self._remaining_size = max_output_size
        self._total_size = 0
        self._buffer = []

    @abstractmethod
    def record_server_output(self, data):
        """record terminal output (user + server originated)
        """
        self._total_size += len(data)
        if self._remaining_size > 0:
            part = data[:self._remaining_size]
            self._buffer.append(part)
            self._remaining_size = max(0, self._remaining_size - len(part))

    @property
    def total_size(self):
        return self._total_size

    def output_as_string(self):
        return ''.join(self._buffer)


def spawn_and_record(recorder, func, parent_func, *args, **kwargs):
    script = ptysnoop.Script(recorder)
    return script.run(func, parent_func, *args, **kwargs)
