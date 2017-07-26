""" Contains the unittest class and methods that test the StorageHeartbeat
    class.
"""

import unittest
import multiprocessing
import threading
import cPickle as pickle

from mock import MagicMock, patch, call
from Queue import Queue, Empty

from client import StorageHeartbeat
from shared import ProcessData, Message

class TestHeartbeat(object):
    """The TestHeartbeat contains the unittests that are used for testing
       the StorageHeartbeat class.
    """

    class MockProcess(object):
        """ The MockProcess contains a limited subset of attribute of
            a multiprocessing.Process.
        """
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class MockSocket(object):
        """ The MockSocket contains a limited subset of attribute of
            a socket.  It is primarily used to push Messages sent to
            the server onto a queue for immediate inspection.
        """
        def __init__(self, queue, test):
            self.queue = queue
            self.test = test

        def sendall(self, message):
            """ This immitates the sendall method of a socket.
                In its place, this method extracts the original
                message sent over the 'socket' and puts it onto
                a queue for processing.
            """
            reg = re.compile(':::(\d+):::')
            match = reg.match(message)
            self.test.assertIsNotNone(match)
            offset = len(match.group(0))

            try:
                size = int(match.group(1))
            except ValueError:
                size = None

            message = message[offset:]
            message = pickle.loads(message)
            self.queue.put((size, message))

        def close(self):
            pass

    def setUp(self):
        """ Set up a StorageHeartbeat instance at the beginning of each tests.
            The StorageHeartbeat will be provided with a fake consumer and monitor
            which it will communicate with.  It will also be provided a fake
            socket to send messages to a non-existant server.
        """
        # This Queue and Pipe let heartbeat send and receive messages to the
        # fake child client processes, and have those messages processed here.
        self.queue = Queue()
        self.consumer_master, self.consumer_slave = multiprocessing.Pipe()
        self.monitor_master, self.monitor_slave = multiprocessing.Pipe()

        # Only one consumer
        self.consumer = ProcessData(process=self.MockProcess(id=0,
                                                             name='TestConsumer'),
                                    pipe=self.consumer_slave)

        self.monitor = ProcessData(process=self.MockProcess(id=0,
                                                            name='TestMonitor'),
                                   pipe=self.monitor_slave)

        # Messages that StorageHeartbeat puts on the socket for the server
        # Are quickly decoded again and put on this queue for verification
        self.socket_queue = Queue()

        # We use MockSocket to impersonate a real socket
        self.socket = self.MockSocket(self.socket_queue, self)

        self.dut = StorageHeartbeat(consumers=[self.consumer],
                                    monitor=self.monitor,
                                    report_in=self.queue,
                                    runtime=10,
                                    poll_period=5,
                                    client_socket=self.socket)

    def get_message_from_queue(self):
        """ A method used by tests to attempt to get an expected method
            from the messaging queue.
            Fails if the get() times out because it is empty.
        """
        message = None, None

        try:
            message = self.queue.get(block=True, timeout=3)
        except Empty:
            self.fail(msg='Queue get() failed empty')

        return message

    def test_send_server_message(self):
        """ Test the _send_message_to_server method.
            Validate that the received message is the same as the sent one.
        """
        message = 'abcdefg'
        self.dut._send_message_to_server(message)

        self.assertFalse(self.socket_queue.empty())
        size, received = self.get_message_from_queue()

        self.assertIsNotNone(received)
        if received is None:
            return

        self.assertIsNotNone(size)
        if size is None:
            return

        fail_size = 'Message length {} Received length {}'.format(len(message),
                                                                  size)
        self.assertEqual(size, len(message), msg=fail_size)

        fail_contents = 'Message: ({}) Received: ({})'.format(message, received)
        self.assertEqual(message, received, msg=fail_contents)

    def test_kill(self):
        """ Tests the _kill_all method.
            The _poll_processes function is not tested here, only that
            it was called once.
        """
        self.dut._poll_processes = MagicMock()
        self.dut._kill_all()
        self.assertTrue(self.dut._poll_processes.call_count, 1)

    def test_heartbeat(self):
        """ Tests the _do_heartbeat method.
            The _poll_processes function is not tested here, only that
            it was called three times.
        """
        self.dut._poll_processes = MagicMock()
        self.dut._do_heartbeat()
        self.assertEqual(self.dut._poll_processes.call_count, 3)

    def handle_process_pipes(self, message, response_type):
        """ Method used when testing _poll_processes.
            This checks the content of the messages on the fake
            process' pipes and send appropriate responses.
            This also checks the aggregated message that get
            sent to the server.
        """
        # Check slave pipes for message
        assertTrue(self.monitor_slave.poll(3))
        if self.monitor_slave.poll():
            assertEqual(self.monitor_slave.recv(), message)

        assertTrue(self.consumer_slave.poll(3))
        if self.consumer_slave.poll():
            assertEqual(self.consumer_slave.recv(), message)

        # Send responses on slaves to heartbeat
        response = Message(name=None,
                           date_time=None,
                           type=response_type)
        self.monitor_slave.send(response)
        self.consumer_slave.send(response)

        # check server socket for heartbeat aggregate packet
        size, received = self.get_message_from_queue()

        self.assertIsNotNone(received)
        if received is None:
            return

        self.assertIsNotNone(size)
        if size is None:
            return

        self.assertIsInstance(received, Message)

        self.assertEqual(message.type, response_type)
        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, 'Heartbeat')

        self.assertIsInstance(message.payload(0), list)
        self.assertEqual(len(message.payload(0)), 2)

        self.assertIsInstance(message.payload(1), set)
        self.assertEqual(len(message.payload(1)), 0)

    def test_poll_processes(self):
        """ Tests the _poll_processes method.
            Sends a generic message using _poll_processes and verifies
            its reaction via a thread running along side the dut.
        """
        message='abcdefg'
        response_type = 'TEST'
        t = threading.Thread(target=self.handle_process_pipes, args=(message, response_type))
        t.start()

        self.dut._poll_processes(message=message,
                                 timeout=2,
                                 response_type=response_type)

        t.join()

    def handle_message_queue(self):
        """ Drives the _process_message_queue by injecting messages into
            its queue and verifying that the correct messages get sent to
            the server.
        """
        # Add some dummy messages to the queue
        message = ['dummy1', 'dummy2', 'dummy3']
        for message in messages:
            self.queue.put(message)

        time.sleep(1)
        # Send kill event
        self.dut.kill.set()

        time.sleep(1)

        assertTrue(self.dut.queue_empty.is_set())
        # _process_message_queue is done

        # Check that dummy messages are in server socket queue
        for message in messages:
            size, received = self.get_message_from_queue()

            self.assertIsNotNone(received)
            if received is None:
                return

            self.assertIsNotNone(size)
            if size is None:
                return

            fail_size = 'Message length {} Received length {}'.format(len(message),
                                                                    size)
            self.assertEqual(size, len(message), msg=fail_size)

            fail_contents = 'Message: ({}) Received: ({})'.format(message, received)
            self.assertEqual(message, received, msg=fail_contents)

    def test_process_message_queue(self):
        """ Test the _process_message_queue method.
            Starts a thread to run along side the method which performs the test.
        """
        t = threading.Thread(target=self.handle_message_queue)
        t.start()

        self.dut._process_message_queue()

        t.join()


