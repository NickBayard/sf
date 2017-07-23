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


    def setUp(self):
        self.queue = Queue()

        address = ('127.0.0.1', 10000)

        # Start the server
        self.server = self.MyTCPServer(address, Handler, self.queue)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.start()

        # Start a client connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(address)

    def tearDown(self):
        self.socket.close()
        self.server.shutdown()
        self.server_thread.join()

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
