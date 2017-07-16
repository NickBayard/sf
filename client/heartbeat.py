'''Enter module docstring here'''

import os
import time
import socket
import cPickle as pickle
from datetime import datetime
from threading import Thread, Event
from Queue import Empty

from shared import Message, configure_logging

class StorageHeartbeat(object):
    HEARTBEAT_RESPONSE_TIMEOUT = 3
    HEARTBEAT_KILL_TIMEOUT = 10

    def __init__(self, consumers, monitor, report_in, runtime,
                 poll_period, server, log_level='INFO'):
        self.consumers = consumers
        self.monitor = monitor
        self.report_in = report_in
        self.runtime = runtime
        self.poll_period = poll_period
        self.log = configure_logging(log_level, 'Client')
        self.server = server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.log.info("Connecting to {}".format(self.server))
        self.socket.connect(self.server)

    def _log_message_received(self, message):
        self.log.info('Message received from {}_{}: {}'.format(message.name,
                                                               message.id,
                                                               repr(message)))

    def _log_message_sent(self, message, process):
        self.log.info('Message sent to {}_{}: {}'.format(process.name,
                                                         process.id,
                                                         repr(message)))
    def _handle_heartbeat(self, responses, missing):
        pass

    def _handle_kill(self, responses, missing):
        pass

    def _poll_processes(self, message, timeout, response_type, handler):
        #Send the message to the monitor and all consumers
        self.monitor.pipe.send(message)
        self._log_message_sent(message, self.monitor.process)

        for consumer in self.consumers:
            consumer.pipe.send(message)
            self._log_message_sent(message, consumer.process)

        # Poll the monitor and self.consumers until we get all responses or until
        # we timeout.
        responses = []
        response_stop = time.time() + timeout

        while time.time() < response_stop and \
            len(responses) < len(self.consumers) + 1:

            if self.monitor.pipe.poll():
                response = self.monitor.pipe.recv()
                self._log_message_received(response)
                if response.type == response_type:
                    responses.append(response)

            for consumer in self.consumers:
                if consumer.pipe.poll():
                    response = consumer.pipe.recv()
                    self._log_message_received(response)
                    if response.type == response_type:
                        responses.append(response)

        missing_responses = set([])
        if len(responses) < len(self.consumers) + 1:
            # We must have timed out.  Check for missed responses
            responding_processes = set([(proc.name, proc.id) for proc in responses])
            processes = set([(consumer.proc.name, consumer.proc.id) for consumer in consumers])
            processes.add((self.monitor.process.name, self.monitor.process.id))

            missing_responses = processes - responding_processes

        handler(responses, missing_responses)

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
                                 response_type='HEARTBEAT',
                                 handler=self._handle_heartbeat)

            # Subtract the elapsed time from the poll_period for
            # more accurate heartbeat intervals
            sleep_time = self.poll_period - (time.time() - poll_start_time)
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
                             response_type='STOP',
                             handler=self._handle_kill)

    def _process_message(self, message):
        self._log_message_received(message)

        # pickle the message into a string and send to the server
        # Not secure but sufficient for our purposes
        ps_message = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)

        # Add a simple prefix to our message indicating the length that the
        # server should expect.  This allows us to leave the socket open for
        # all messages
        ps_message = str(len(ps_message)) + ':::' + ps_message
        self.socket.sendall(ps_message)

    def _process_message_queue(self):
        while not self.kill.is_set():
            # We just need a block to break from if an Empty exception occurs
            for _ in [None]:
                try:
                    message = self.report_in.get(block=True, timeout=2)
                except Empty:
                    break

                self._process_message(message)

        # Kill event was set. Finish processing the remaining events in the queue
        while not self.report_in.empty():
            try:
                message = self.report_in.get()
            except Empty:
                break # We shouldn't ever get here

            self._process_message(message)

    def run(self):
        self.kill = Event() # This signals _process_message_queue to finish up
        t = Thread(target=self._process_message_queue)
        t.start()

        # Let _do_heartbeat decide how long to run for
        self._do_heartbeat()
        # Then kill all child processes
        self._kill_all()

        # Finish processing remaining messages from child processes
        self.kill.set()
        t.join()
        self.socket.close()
