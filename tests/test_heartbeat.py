import unittest
import multiprocessing
import threading
import cPickle as pickle

from mock import MagicMock, patch, call
from Queue import Queue, Empty

from client import StorageHeartbeat
from shared import ProcessData, Message

class TestHeartbeat(object):

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

    def test_heartbeat(self):
        self.dut._poll_processes = MagicMock()
        self.dut._do_heartbeat()
        self.assertEqual(self.dut._poll_processes.call_count, 3)

    def handle_process_pipes(self, message, response_type):
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
        message='abcdefg'
        response_type = 'TEST'
        t = threading.Thread(target=self.handle_process_pipes, args=(message, response_type))
        t.start()

        self.dut._poll_processes(message=message,
                                 timeout=2,
                                 response_type=response_type)

        t.join()

    def handle_message_queue(self):
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
        t = threading.Thread(target=self.handle_message_queue)
        t.start()

        self.dut._process_message_queue()

        t.join()


