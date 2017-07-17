'''Enter module docstring here'''

import os
import time
import cPickle as pickle
from socket import error as SocketError
from datetime import datetime
from threading import Thread, Event
from Queue import Empty

from shared import Message, configure_logging

class StorageHeartbeat(object):
    HEARTBEAT_RESPONSE_TIMEOUT = 3
    HEARTBEAT_KILL_TIMEOUT = 10

    def __init__(self, consumers, monitor, report_in, runtime,
                 poll_period, client_socket, log_level='INFO'):
        self.consumers = consumers
        self.monitor = monitor
        self.report_in = report_in
        self.runtime = runtime
        self.poll_period = poll_period
        self.socket = client_socket
        self.log = configure_logging(log_level, 'Client')

    def _log_message_received(self, message):
        self.log.info('Message received from {}_{}: {}'.format(message.name,
                                                               message.id,
                                                               repr(message)))

    def _log_message_sent(self, message, process):
        self.log.info('Message sent to {}_{}: {}'.format(process.name,
                                                         process.id,
                                                         repr(message)))

    def _send_message_to_server(self, message):
        # pickle the message into a string and send to the server
        # Not secure but sufficient for our purposes
        ps_message = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)

        # Add a simple prefix to our message indicating the length that the
        # server should expect.  This allows us to leave the socket open for
        # all messages
        ps_message = ':::{}:::{}'.format(len(ps_message), ps_message)
        try:
            self.socket.sendall(ps_message)
        except SocketError:
            # Server socket seems to have gone away.  Abort
            self.kill.set()

    def _poll_processes(self, message, timeout, response_type, wait_to_send=None):
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

        #if wait_to_send is not None:
            #wait_to_send.wait()

        message = Message(name='Heartbeat',
                          id=0,
                          date_time=datetime.now(),
                          type=response_type,
                          payload=(responses, missing_responses))
        self._send_message_to_server(message)
        self.log.info('Message send to server: {}'.format(repr(message)))

    def _do_heartbeat(self):
        heartbeat_stop = time.time() + self.runtime

        # Stop running if the kill event is set or if we've been running
        # for specified runtime
        while time.time() < heartbeat_stop and not self.kill.is_set():
            poll_start_time = time.time()

            # Send out heartbeat requests
            message = Message(name='Heartbeat',
                              id=0,
                              date_time=None,
                              type='HEARTBEAT',
                              payload=None)

            self._poll_processes(message=message,
                                 timeout=self.HEARTBEAT_RESPONSE_TIMEOUT,
                                 response_type='HEARTBEAT')

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
                             wait_to_send=self.queue_empty)

    def _process_message_queue(self):
        while not self.kill.is_set():
            try:
                message = self.report_in.get(timeout=2)
            except Empty:
                continue

            self._log_message_received(message)
            self._send_message_to_server(message)

        # Kill event was set. Finish processing the remaining events in the queue
        while not self.report_in.empty():
            try:
                message = self.report_in.get(block=False)
            except Empty:
                break # We shouldn't ever get here

            self._log_message_received(message)
            self._send_message_to_server(message)

        self.queue_empty.set()

    def run(self):
        self.kill = Event() # This signals _process_message_queue to finish up

        # Event used to delay sending STOP message to server until all messages
        # in the queue have been handled
        self.queue_empty = Event()

        t = Thread(target=self._process_message_queue)
        t.start()

        # Let _do_heartbeat decide how long to run for
        self._do_heartbeat()
        # Then kill all child processes
        self._kill_all()

        # Finish processing remaining messages from child processes
        self.log.info("setting hb kill")
        self.kill.set()
        t.join()

        self.socket.close()
