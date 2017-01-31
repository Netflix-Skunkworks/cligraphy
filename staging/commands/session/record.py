#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

from cligraphy.core import capture, decorators
from cligraphy.core.capture import fmt_capnp
import logging
import os


def shell():
    """ Run out command
    """
    cmdline = ['/bin/bash', '/bin/bash', '-l']
    logging.info("Running [%s] in pid %d", ' '.join(cmdline), os.getpid())
    os.execl(*cmdline)


@decorators.tag(decorators.Tag.interactive)
def main(args):
    logging.basicConfig(level=logging.INFO)
    recorder = fmt_capnp.CapnpSessionRecorder()
    print 'Session start - recording in %s' % (recorder.filename)
    capture.spawn_and_record(recorder, shell, None)
    print 'Session done - recorded in %s' % (recorder.filename)
