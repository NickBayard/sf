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
    
    message_dispatch = { 'HEARTBEAT'    : handle_aggregate_response,
                         'START'        : handle_start,
                         'STOP'         : handle_stop,
                         'ROLLOVER'     : handle_rollover,
                         'MONITOR'      : handle_monitor,
                         'MONITOR_ERROR': handle_monitor }

    def __init__(self, log_level, server_address, RequestHandlerClass):
        TCPServer.__init__(self,
                           server_address=server_address,
                           RequestHandlerClass=RequestHandlerClass)
        self.manager = multiprocessing.Manager()
        self.message_queue = self.manager.Queue()
        self.log = configure_logging(log_level, 'Server')

        self.kill = threading.Event()
        self.thread = threading.Thread(target=self.watch_queue)
        self.thread.start()
        self.client_messages = {}

    def watch_queue(self):
        while not self.kill.is_set():
            client, message = self.message_queue.get()

            # Handle each type of message
            dispatch_string = message_dispatch[message.type](message)
            self.log.info("Received {} from client @ {}{}".format(message.type,
                                                                  client,
                                                                  dispatch_string))

            # Aggregate messages per client for report generation
            self.client_messages.setdefault(client, []).append(message)

    def handle_aggregate_response(self, message):
        no_response_string = ''

        # payload[1] contains the set of non-responsive client processes
        if len(message.payload[1]):
            nonresponding = ['{}_{}'.format(process[0], process[1])
                                  for process in message.payload[1]]
            no_response_string = '; Child processes did not respond: {}'.format(
                ', '.join(nonresponding))

        return no_response_string

    def handle_stop(self, message):
        return handle_aggregate_response(message)

    def handle_start(self, message):
        return ''

    def handle_rollover(self, message):
        return '; {}_{} {}/{} chunks - {}'.format(message.name,
                                                  message.id,
                                                  message.payload.size,
                                                  message.payload.chunk,
                                                  message.payload.path)

    def handle_monitor(self, message):
        # Building the string for readability
        monitor_name = '{}_{}'.format(message.name, message.id)
        child_process = '{}_{}: pid {},'.format(message.payload.name,
                                                 message.payload.id,
                                                 message.payload.pid)
        data = 'mem {}, cpu {}, time {}'.format(message.payload.mem,
                                                message.payload.cpu,
                                                message.paylaod.etime)

        return '; {} monitoring {} {}'.format(monitor_name, child_process, data)
