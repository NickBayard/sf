import os
import unittest
import socket
import threading
import cPickle as pickle

from SocketServer import TCPServer
from Queue import Queue, Empty

from server import Handler


class TestHandler(unittest.TestCase):

    class MyTCPServer(TCPServer):

        allow_reuse_address = True

        def __init__(self, server_address, RequestHandlerClass, queue):
            # TCPServer/BaseServer are not new style classes and cannot use super()
            TCPServer.__init__(self,
                            server_address=server_address,
                            RequestHandlerClass=RequestHandlerClass)

            self.queue = queue
            self.log = None

        def finish_request(self, request, client_address):
            """Creates a BaseHandlerClass instance that handles the request.

            Overrides BaseServer.finish_request in order to overload the
            RequestHandlerClass instantiation.

                Args:
                    request: A socket request object.
                    client_address: A tuple containing the client ip/port.
            """
            self.RequestHandlerClass(request, client_address, self, self.queue)


    @classmethod
    def setUpClass(cls):
        """ Set up the server and client sockets at the class level.
            Doing this at the test level may render a socket unable to
            be reused.
        """
        cls.queue = Queue()

        address = ('127.0.0.1', 10000)

        # Start the server
        cls.server = cls.MyTCPServer(address, Handler, cls.queue)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.start()

        # Start a client connection
        cls.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cls.socket.connect(address)

    @classmethod
    def tearDownClass(cls):
        """ Tear down the server and client sockets at the class level."""
        cls.socket.close()
        cls.server.shutdown()
        cls.server_thread.join()

    def send_message_to_server(self, message):
        message = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)
        message = ':::{}:::{}'.format(len(message), message)
        try:
            self.socket.sendall(message)
        except socket.error:
            self.fail('Socket closed')

    def test_handler_simple(self):
        # Send some messages to the handler
        message = 'abcdefg'
        self.send_message_to_server(message)

        # Check the messages on the queue
        received = self.queue.get(block=True, timeout=2)

        fail_receive = 'Message: ({}) Received: ({})'.format(message, received)
        self.assertEqual(message, received, msg=fail_receive)

    def test_handler_fragmented(self):
        # Send some messages to the handler
        payload = 'abcdefg'
        pickled = pickle.dumps(payload, pickle.HIGHEST_PROTOCOL)
        prefixed = ':::{}:::{}'.format(len(pickled), pickled)

        messages = [prefixed[:-4], prefixed[-4:]]

        for message in messages:
            try:
                self.socket.sendall(message)
            except socket.error:
                self.fail('Socket closed')

        # Check the messages on the queue
        try:
            received = self.queue.get(block=True, timeout=2)
        except Empty:
            self.fail('Queue empty')

        fail_receive = 'Message: ({}) Received: ({})'.format(payload, received)
        self.assertEqual(payload, received, msg=fail_receive)
