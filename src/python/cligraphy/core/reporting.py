#!/usr/bin/env python
# Copyright 2014 Netflix, Inc.

from cligraphy.core.tracking import TRACKING

import threading
from Queue import Queue, Empty, Full
import collections

import requests

import logging
import os
import socket
import time

ReportingEvent = collections.namedtuple('ReportingEvent', 'name,args,kwargs')


class Reporter(object):

    def report_command_start(self, command_line):
        """Report command execution"""
        pass

    def report_command_output(self, output):
        """Report command output"""
        pass

    def report_command_exit(self, exit_code):
        """Report command exit code"""
        pass

    def start(self):
        """Start this reporter"""
        pass

    def stop(self):
        """Stop this reporter"""
        pass


class NoopReporter(Reporter):
    """Reporter that does nothing"""


class ThreadedReporter(Reporter, threading.Thread):
    """Base class for reporters"""

    idle_period = 10

    def __init__(self):
        super(Reporter, self).__init__(group=None, name='oc-reporter-thread')
        self.daemon = True
        self.queue = Queue(maxsize=16)
        self.stop_event = threading.Event()

    def run(self):
        logging.debug('Starting reporter thread mainloop')
        while True:
            try:
                event = self.queue.get(block=True, timeout=self.idle_period)
                if event:
                    if event.name == 'stop':
                        return
                    func = getattr(self, '_report_%s' % event.name, None)
                    if func:
                        func(*event.args, **event.kwargs)
            except Empty:
                if self.stop_event.is_set():
                    return
                else:
                    try:
                        self._report_idle()
                    except Exception:
                        pass

    def _report(self, event_name, *args, **kwargs):
        event = ReportingEvent(name=event_name, args=args, kwargs=kwargs)
        try:
            self.queue.put(event, block=False)
        except Full:
            logging.debug('Could not put event (name=%s) in reporting queue', event_name, exc_info=True)

    def _report_idle(self):
        pass

    def report_command_start(self, command_line):
        """Report command execution"""
        self._report('command_start', command_line)

    def report_command_output(self, output):
        """Report command output"""
        self._report('command_output', output)

    def report_command_exit(self, exit_code):
        """Report command exit code"""
        self._report('command_exit', exit_code)

    def start(self):
        threading.Thread.start(self)

    def stop(self, timeout=1.5):
        self.stop_event.set()
        self._report('stop')
        logging.debug('Waiting on reporter thread for up to %s second', timeout)
        self.join(timeout=timeout)
        if self.isAlive():
            logging.debug('Reported thread is still running')


def disable_ssl_warnings():
    import requests.packages.urllib3
    requests.packages.urllib3.disable_warnings()


class ToolsPadReporter(ThreadedReporter):

    timeout = 0.75

    def __init__(self, cligraph):
        super(ToolsPadReporter, self).__init__()
        self.cligraph = cligraph
        self.requests_session = requests.Session()
        self.requests_session.headers.update({'User-Agent': 'octools:%s@%s' % (os.getenv('USER'), socket.gethostname())})
        self.created = False
        self.session_endpoint = None
        self.create_event_endpoint = None
        self.idle_endpoint = '%s' % self.cligraph.conf.report.server
        self.create_session_endpoint = '%s/api/v0.1/execution' % self.cligraph.conf.report.server
        disable_ssl_warnings()

    def _report_idle(self):
        self.requests_session.head(self.idle_endpoint)

    def _report_command_start(self, command_line):
        try:
            response = self.requests_session.post(self.create_session_endpoint, data={
                'uuid': TRACKING.execution_uuid,
                'session_uuid': TRACKING.session_uuid,
                'user_email': self.cligraph.conf.user.email,
                'start_stamp': int(time.time()),
                'command_line': ' '.join(command_line)
            }, timeout=self.timeout)
            if response.status_code == 201:
                self.created = True
                self.session_endpoint = '%s%s' % (self.cligraph.conf.report.server, response.json()['uri'])
                self.create_event_endpoint = '%s/event' % (self.session_endpoint)
            else:
                response.raise_for_status()

        except requests.exceptions.RequestException:
            logging.debug('Could not report command start', exc_info=True)

    def _report_command_output(self, output):
        if not self.created:
            return
        try:
            response = self.requests_session.post(self.create_event_endpoint, data={
                'stamp': int(time.time()),
                'type': 'output',
                'body': output,
            }, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logging.debug('Could not report comand output', exc_info=True)

    def _report_command_exit(self, exit_code):
        if not self.created:
            return
        try:
            response = self.requests_session.patch(self.session_endpoint, data={
                'end_stamp': int(time.time()),
                'exit_code': exit_code,
            }, timeout=self.timeout)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            logging.debug('Could not report command exit', exc_info=True)
