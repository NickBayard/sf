"""Contains the unittest class and methods that test the Handler class."""

import unittest
import socket
import threading
import cPickle as pickle

from SocketServer import TCPServer
from Queue import Queue, Empty

from server import Handler


class TestHandler(unittest.TestCase):
    """The TestHandler contains unittests that are used for testing the Handler
       class.
    """

    class MyTCPServer(TCPServer):
        """This acts as a simple socket server for the Handler class to hook into.
           It allows tests to inject fake socket connection requests and verify
           that the handler has correctly decoded the packets.
        """

        allow_reuse_address = True

        def __init__(self, server_address, RequestHandlerClass, queue):
            """Initialize a MyTCPServer with:

               Args:
                server_address:  Atuple containing the server ip and port
                    that the server should bind/listen to.
                RequestHandlerClasss: This will be the Handler class that
                    we want to test.
                queue: A queue for the Handler to place extracted messages
                    into.
            """
            # TCPServer/BaseServer are not new style classes and cannot use super()
            TCPServer.__init__(self,
                            server_address=server_address,
                            RequestHandlerClass=RequestHandlerClass)

            # Handler will place extracted messages into this queue for
            # processing later.
            self.queue = queue

            # Turn off logging in Handler
            self.log = None

        def finish_request(self, request, client_address):
            """Creates a BaseHandlerClass instance that handles the request.

            Overrides BaseServer.finish_request in order to overload the
            RequestHandlerClass instantiation.

                Args:
                    request: A socket request object.
                    client_address: A tuple containing the client ip/port.
            """
            # RequestHandler class is also given a reference to the server
            # as well as a queue for processing messages.
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
        """Method that encodes and sends a message to the server. Test
           classes use this method to reduce duplicate code.

           Args:
            message: The content that should be sent to the server.

           Raises:
            socket.error if sending data over a socket fails.
        """
        message = pickle.dumps(message, pickle.HIGHEST_PROTOCOL)
        message = ':::{}:::{}'.format(len(message), message)
        try:
            self.socket.sendall(message)
        except socket.error:
            self.fail('Socket closed')

    def test_handler_simple(self):
        """ Test a sending a simple message to the handler for extraction. """
        message = 'abcdefg'
        self.send_message_to_server(message)

        # Check the messages on the queue
        received = self.queue.get(block=True, timeout=2)

        fail_receive = 'Message: ({}) Received: ({})'.format(message, received)
        self.assertEqual(message, received, msg=fail_receive)

    def test_handler_fragmented(self):
        """ Test sending a fragmented message to the server. """ 
        # We can't use send_message_to_server here so that we can split it
        # into two chunks
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
