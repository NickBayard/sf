"""Contains the definition for the StorageHeartbeat class."""

import time
import cPickle as pickle
from socket import error as SocketError
from datetime import datetime
from threading import Thread, Event
from Queue import Empty

from shared import Message, configure_logging


class StorageHeartbeat(object):
    """The StorageHeartbeat runs on the parent process of the client instance.
       It acts as the master to the StorageConsumer and StorageMonitor
       instances.

       Communication of task status from all children is done
       via a multiprocessing.Queue.  Additionally, there is a multiprocessing.Pipe
       connected to each child process for sending HEARTBEAT and KILL requests.

       All status tasks received on the queue are pickled and sent to the server
       over a socket.  HEARTBEAT and KILL responses are aggregated, pickled,
       and sent to the server over the same socket.
    """

    #These constants could optionally be converted to configuration parameters

    # (seconds) HEARTBEAT requests to child process must be reponded to within
    # this amout of time.
    HEARTBEAT_RESPONSE_TIMEOUT = 3
    # (seconds) KILL requests to child process must be reponded to within
    # this amout of time.
    HEARTBEAT_KILL_TIMEOUT = 10

    def __init__(self, consumers, monitor, report_in, runtime,
                 poll_period, client_socket, log_level=None):
        """Initializes a StorageHeartbeat with:

            Args:
                consumers: An iterable of ProcessData objects for the
                    StorageConsumer processes.
                monitor: A ProcessData object for the StorageMonitor process.
                report_in: Queue containing all child processes status.
                runtime: The configured runtime of the client.
                poll_period: The interval (seconds) on which to send
                    HEARTBEAT requests to child processes and then forward
                    the results to the server.
                client_socket: A connected socket to the server.
                log_level: A string matching the logging level.
                    (e.g. DEBUG, INFO, WARNING)
        """
        self.consumers = consumers
        self.monitor = monitor
        self.report_in = report_in
        self.runtime = runtime
        self.poll_period = poll_period
        self.socket = client_socket
        self.log = configure_logging(log_level, 'Client') \
            if log_level is not None else None

    def _log_message_received(self, message):
        """A helper method to log a message received from a child process.

            Args:
                message: A Message object received from a child process.
        """
        self.log.info('Message received from {}_{}: {}'.format(message.name,
                                                               message.id,
                                                               repr(message)))

    def _log_message_sent(self, message, process):
        """A helper method to log a message sent to a child process.

            Args:
                message: A Message object sent to a child process.
                process: The Process to which the message was sent.
        """
        self.log.info('Message sent to {}_{}: {}'.format(process.name,
                                                         process.id,
                                                         repr(message)))

    def _send_message_to_server(self, message):
        """Pickle a message and send it to the server.

           Sets the kill Event should the socket no longer be open.

            Args:
                message: A Message object to be sent to the server.
        """
        # pickle the message into a string
        # Not secure but sufficient for our purposes
        ps_message = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)

        # Add a simple prefix to our message indicating the length that the
        # server should expect.  This allows us to leave the socket open for
        # all messages on this connection.
        ps_message = ':::{}:::{}'.format(len(ps_message), ps_message)
        try:
            self.socket.sendall(ps_message)
        except SocketError:
            # Server socket seems to have gone away.  Abort!
            self.kill.set()

    def _poll_processes(self, message, timeout, response_type, wait_to_send=None):
        """This method sends a message to all children processes and collects
           the response messages from each.  Processes that fail to respond are
           aggregated as a list of tuple of (name, id). The process responses
           and failed response list are sent to the server.

           This method is used by _do_heartbeat and _kill_all to prevent code
           duplication.

            Args:
                message: A Message object to send to all children.
                timeout: Time (s) to wait for responses.
                response_type: The Message.type expected in the responses.
                wait_to_send: And event signal that we wait on before sending
                    the message to the server.
        """
        #Send the message to the monitor and all consumers
        self.monitor.pipe.send(message)
        self._log_message_sent(message, self.monitor.process)

        for consumer in self.consumers:
            consumer.pipe.send(message)
            self._log_message_sent(message, consumer.process)

        # Poll the monitor and consumers until we get all responses or until
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
            processes = set([(consumer.process.name, consumer.process.id) for
                             consumer in self.consumers])
            processes.add((self.monitor.process.name, self.monitor.process.id))

            # Items in the processes set but not in the responding_processes set
            # (symmetric difference) are the missing responses
            missing_responses = processes - responding_processes

        if wait_to_send is not None:
            # Signal message queue to finish processing
            self.kill.set()
            # Wait until work is done
            wait_to_send.wait()

        message = Message(name='Heartbeat',
                          id=0,
                          date_time=datetime.now(),
                          type=response_type,
                          payload=(responses, missing_responses))
        self._send_message_to_server(message)
        self.log.info('Message sent to server: {}'.format(repr(message)))

    def _do_heartbeat(self):
        """Periodically send heartbeat requests to child processes and forward
           results to the server until:
            1. Runtime is elapsed
            2. Kill event gets set (socket was closed)
        """
        heartbeat_stop = time.time() + self.runtime

        # Stop running if the kill event is set or if we've been running
        # for specified runtime
        while time.time() < heartbeat_stop and not self.kill.is_set():
            poll_start_time = time.time()

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
        """Send kill message to all child processes.

           This run after the client runtime has elapsed or the kill event
           has been set.
        """
        message = Message(name='Heartbeat',
                          id=0,
                          date_time=None,
                          type='KILL',
                          payload=None)

        # Wait to send STOP message to server until the message queue has been
        # fully processed.  This hopes to arrange this as the last message to
        # arrive at the server.
        self._poll_processes(message=message,
                             timeout=self.HEARTBEAT_KILL_TIMEOUT,
                             response_type='STOP',
                             wait_to_send=self.queue_empty)

    def _process_message_queue(self):
        """Process messages in the report_in queue.

           The self.kill Event signals this thread to process the
           queue until empty and then exit.

           This method runs as a separate background thread while
           _do_heartbeat and _kill_all run in the foreground.
        """
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

        # Signal that the queue has been fully processed
        self.queue_empty.set()

    def run(self):
        """This is the main entry point for StorageHeartbeat."""
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
        t.join()

        self.socket.close()
