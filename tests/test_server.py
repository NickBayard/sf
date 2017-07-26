import unittest
import socket

from mock import MagicMock
from multiprocessing import Event

from server import Server, ClientData, Handler
from shared import Message


class TestServer(unittest.TestCase):

    class MockClient(object):

        def __init__(self, done=False):
            self.messages = []
            self.kill = Event()
            self.done = done

    @classmethod
    def setUpClass(cls):
        """ Set up a Server instance to test before all tests are run.
            Since SocketServer sets up its own socket connection, we must
            also create a client socket connection for sending messages to the server.
        """
        address = ('127.0.0.1', 10001)
        cls.dut = Server(log_level='INFO',
                         server_address=address,
                         RequestHandlerClass=Handler,
                         report_path='./temp/')

        cls.dut.log.info = MagicMock()  # Turn off logging

        #cls.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #cls.socket.connect(('127.0.0.1', 10000))

    @classmethod
    def tearDownClass(cls):
        """ Close the server and client sockets after all tests are done. """
        #cls.dut.shutdown()
        #cls.socket.close()
        pass

    def tearDown(self):
        self.dut.clients.clear()

    def test_handle_message(self):
        """ Test the _handle_message method.
            Use a start message and verify that the message
            was logged and added to the queue.
        """
        message=Message(name='TestMessage',
                        id=0,
                        date_time=None,
                        type='START',
                        payload=None)

        client = self.MockClient()

        # Stash away the mocked methods since we reuse the same server
        # across tests
        _handle_start = self.dut._handle_start
        self.dut.message_dispatch['START'] = MagicMock()

        self.dut._handle_message(message=message,
                                 client=client,
                                 client_address='TESTADDRESS')

        self.assertEqual(self.dut.message_dispatch['START'].call_count, 1)
        self.assertEqual(self.dut.log.info.call_count, 1)
        self.assertEqual(len(client.messages), 1)
        self.assertIs(client.messages[0], message)

        # Restore previously mocked methods
        self.dut.message_dispatch['START'] = _handle_start

    def test_handle_stop(self):
        """ Test the _handle_stop method.
            Verify that the kill Event is set.
        """
        message=Message(name='TestMessage',
                        id=0,
                        date_time=None,
                        type='STOP',
                        payload=None)

        client = self.MockClient()

        # Stash away mocked method
        _handle_aggregate_response = self.dut._handle_aggregate_response
        self.dut._handle_aggregate_response = MagicMock()

        self.dut._handle_stop(message, client)

        self.assertTrue(client.kill.is_set())
        self.assertEqual(self.dut._handle_aggregate_response.call_count, 1)

        #Restore previously mocked method
        self.dut._handle_aggregate_response = _handle_aggregate_response

    def create_clients(self, clients_done=[]):
        """ Method for loading clients dictionary with MockClient with
            prescribed setting in 'done' attribute.
        """
        for id, done in enumerate(clients_done):
            self.dut.clients[id] = self.MockClient(done)

    def test_no_clients_done(self):
        """ Test the _are_all_clients_done method.
            Validate that all clients set to false returns false.
        """
        self.create_clients([False, False, False, False])

        self.assertFalse(self.dut._are_all_clients_done())

    def test_all_clients_done(self):
        """ Test the _are_all_clients_done method.
            Validate that all clients set to true returns true.
        """
        self.create_clients([True, True, True, True])

        self.assertTrue(self.dut._are_all_clients_done())

    def test_some_clients_done(self):
        """ Test the _are_all_clients_done method.
            Validate that some clients set to true returns false.
        """
        self.create_clients([True, False, True, False])

        self.assertFalse(self.dut._are_all_clients_done())
