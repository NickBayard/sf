import re
import cPickle as pickle
import threading
import multiprocessing
from Queue import Queue

from shared import configure_logging
from SocketServer import TCPServer, BaseRequestHandler

class Handler(BaseRequestHandler):
    def __init__(self, request, client_address, server):
        self.log = server.log
        BaseRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        re_obj = re.compile(':::(\d+):::')
        data = ''
        while True:
            new_message = True
            size = 0
            message = ''
            while True:
                data += self.request.recv(1024)
                if not data:
                    return

                if new_message:
                    match = re_obj.match(data)
                    if match:
                        new_message = False
                        size = int(match.group(1))
                        offset = len(match.group(0))
                        data = data[offset:]
                    else:
                        break

                remaining = size - len(message)
                if len(data) > remaining:
                    # Need to truncate data to get right message length
                    message += data[:remaining]
                    data = data[remaining:]
                else:
                    message += data
                    data = ''

                if len(message) == size:
                    self.send_message(message)
                    break
                # else need to collect more data

    def send_message(self, message):
        message = pickle.loads(message)
        self.server.message_queue.put((self.client_address, message))

class MultiprocessMixin:
    def process_request_process(self, request, client_address):
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        p = multiprocessing.Process(target = self.process_request_process,
                             args = (request, client_address))
        p.start()

class Server(MultiprocessMixin, TCPServer):
    allow_reuse_address = True

    def __init__(self, log_level, server_address, RequestHandlerClass):
        TCPServer.__init__(self,
                           server_address=server_address,
                           RequestHandlerClass=RequestHandlerClass)
        self.manager = multiprocessing.Manager()
        self.message_queue = self.manager.Queue()
        self.log = configure_logging(log_level, 'Server')

        self.thread = threading.Thread(target=self.watch_queue)
        self.thread.start()

    def watch_queue(self):
        while True:
            client, message = self.message_queue.get()
            self.log.info("client {} : {}".format(client, message))
            # TODO process message
            # Look for kill message from a client and kill its handler process
