'''Enter module docstring here'''

from __future__ import print_function
import os
import time
from threading import Thread, Event
from Queue import Empty

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
        self.message_history = {}

    def _handle_heartbeat(self, message):
        print('{} received by HB'.format(repr(message)))
        return message.type == 'HEARTBEAT'

    def _handle_heartbeat_error(self, message):
        pass

    def _handle_kill(self, message):
        print('{} received by HB'.format(repr(message)))
        return message.type == 'STOP'

    def _handle_kill_error(self, message):
        pass

    def _poll_processes(self, message, timeout, handler, error_handler):
        self.monitor_pipe.send(message)
        print('{} sent to monitor'.format(repr(message)))

        for consumer in self.consumers:  #HeartbeatData
            consumer.pipe.send(message)
            print('{} sent to consumer {}'.format(repr(message), consumer.process.id))

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
                    if handler(response):
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
                              payload=None)

            self._poll_processes(message=message,
                                 timeout=self.HEARTBEAT_RESPONSE_TIMEOUT,
                                 handler=self._handle_heartbeat,
                                 error_handler=self._handle_heartbeat_error)

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
                             handler=self._handle_kill,
                             error_handler=self._handle_kill_error)

    def process_message(self, message):
        # message_history is a dict with:
        # keys -> tuple of process name and id/index
        # values -> the received message
        self.message_history.setdefault((message.name, message.id),[]).append(message)
        print('{} received by HB'.format(repr(message)))

    def process_message_queue(self):
        while not self.kill.is_set():
            # We just need a block to break from if an Empty exception occurs
            for _ in [None]:
                try:
                    message = self.report_in.get(block=True, timeout=2)
                except Empty:
                    break

                self.process_message(message)

        # Kill event was set. Finish processing the remaining events in the queue
        while not self.report_in.empty():
            try:
                message = self.report_in.get()
            except Empty:
                break # We shouldn't ever get here

            self.process_message(message)

    def run(self):
        print('Heartbeat pid {}'.format(os.getpid()))

        self.kill = Event() # This signals process_message_queue to finish up
        t = Thread(target=self.process_message_queue)
        t.start()

        # Let _do_heartbeat decide how long to run for
        self._do_heartbeat()
        # Then kill all child processes
        self._kill_all()

        # Finish processing remaining messages from child processes
        self.kill.set()
        print('Kill')
        t.join()

