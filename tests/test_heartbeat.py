import unittest
import multiprocessing
import cPickle as pickle

from mock import MagicMock, patch, call
from Queue import Queue, Empty

from client import StorageHeartbeat
from shared import ProcessData

class TestHeartbeat(object):

    SOCKET_PORT = 1000

    class MockProcess(object):
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class MockSocket(object):
        def __init__(self, queue, test):
            self.queue = queue
            self.test = test

        def sendall(self, message):
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
            #TODO process queue
            pass

    def setUp(self):
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
        message = None, None

        try:
            message = self.queue.get(block=True, timeout=3)
        except Empty:
            self.fail(msg='Queue get() failed empty')

        return message

    def test_send_server_message(self):
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
        self.dut._poll_processes = MagicMock()
        self.dut._kill_all()
        self.assertTrue(self.dut._poll_processes.called)

        call_list = self.dut._poll_processes.call_args_list


