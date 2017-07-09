'''Enter module docstring here'''

from __future__ import print_function
import os
import os.path
import time
import multiprocessing
import threading
from datetime import datetime

from process_containers import Message

class StorageHeartbeat(object):
    HEARTBEAT_RESPONSE_TIMEOUT = 3
    HEARTBEAT_POLL_INTERVAL = 5
    HEARTBEAT_KILL_TIMEOUT = 10

    def __init__(self, consumers, monitor_pipe, report_in, runtime):
        self.consumers = consumers
        self.monitor_pipe = monitor_pipe
        self.report_in = report_in
        self.runtime = runtime

    def _handle_heartbeat(self, message):
        return message.type == 'HEARTBEAT'

    def _handle_heartbeat_error(self, message):
        pass

    def _handle_kill(self, message):
        return message.type == 'STOP'

    def _handle_kill_error(self, message):
        pass

    def _poll_processes(self, message, timeout, handler, error_handler):
        for consumer in self.consumers:  #HeartbeatData
            consumer.pipe.send(message)

        # Poll the monitor and self.consumers until we get all responses or until
        # we timeout.
        responses = []
        response_stop = time.time() + timeout

        while time.time() < response_stop and \
            len(responses) < len(self.consumers) + 1:

            if self.monitor_pipe.poll():
                response = self.monitor_pipe.recv()
                if handler(response):
                    responses.append(response)

            for consumer in self.consumers:
                if consumer.pipe.poll():
                    response = consumer.pipe.recv()
                    if _handler(response):
                        responses.append(response)

        if len(responses) < len(self.consumers) + 1:
            # We must have timed out.  Check for missed responses
            for reponse in responses:
                error_handler(response)

    def _do_heartbeat(self):
        heartbeat_stop = time.time() + self.runtime

        while time.time() < heartbeat_stop:
            poll_start_time = time.time()

            # Send out heartbeat requests
            message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='HEARTBEAT',
                            payload=None))

            self._poll_processes(message=message,
                                 timeout=self.HEARTBEAT_RESPONSE_TIMEOUT,
                                 handler=_handle_heartbeat,
                                 error_handler=_handle_heartbeat_error)

            # Subtract the elapsed time from the HEARTBEAT_POLL_INTERVAL for
            # more accurate heartbeat intervals
            sleep_time = self.HEARTBEAT_POLL_INTERVAL - (time.time() - poll_start_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _kill_all(self):
        # Runtime has ended. Send kill message to all child processes
        message = Message(name='Heartbeat',
                          id=0,
                          date_time=None,
                          type='KILL',
                          payload=None)

        self._poll_processes(message=message,
                             timeout=self.HEARTBEAT_KILL_TIMEOUT,
                             handler=_handle_kill,
                             error_handler=_handle_kill_error)

    def run(self):
        self._do_heartbeat()
        self._kill_all()
