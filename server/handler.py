"""Contains the definition for the Handler class."""

import re
import cPickle as pickle
from SocketServer import BaseRequestHandler


class Handler(BaseRequestHandler):
    """Handler acts as a request handler process for Server.

       It inherits from BaseRequestHandler so handle() gets called
       in BaseRequestHandler.__init__().
    """

    def __init__(self, request, client_address, server, message_queue):
        """Initializes a Handler with:

            Args:
                request: A socket request object.
                client_address: A tuple containing the client ip/port.
                server: The Server instance.
                message_queue: A managed queue for loading Messages
                    received from on the socket.
        """
        self.log = server.log
        self.message_queue = message_queue
        BaseRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        """Extracts Messages from the request socket and sends them to
           the processing thread via message_queue.
        """
        # This is the prefix attached to all Messages from the client.
        # The \d contains the length of the message.
        re_obj = re.compile(':::(\d+):::')
        data = ''

        # Outer loop is entered for each new message
        while True:
            new_message = True
            size = 0
            message = ''

            # Inner loop can construct a Message using multiple receives
            while True:
                data += self.request.recv(1024)
                if not data:
                    return

                # Look for the prefix string and start constructing the Message
                if new_message:
                    match = re_obj.match(data)
                    if match:
                        new_message = False
                        size = int(match.group(1))
                        offset = len(match.group(0))
                        data = data[offset:]
                    else:
                        break

                # Append the data received to the current message
                remaining = size - len(message)
                if len(data) > remaining:
                    # Need to truncate data to get right message length
                    message += data[:remaining]
                    data = data[remaining:]
                else:
                    message += data
                    data = ''

                if len(message) == size:
                    # Message is complete
                    self._send_message(message)
                    break
                # else need to collect more data

    def _send_message(self, message):
        """Unpickle pickle string received over the socket and send the Message
           to the processing thread via message_queue.

            Args:
                message: A pickled Message string.
        """
        message = pickle.loads(message)
        self.message_queue.put(message)
