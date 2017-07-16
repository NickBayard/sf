import re
import cPickle as pickle
import threading
import multiprocessing
from Queue import Queue

from shared import configure_logging
from SocketServer import TCPServer, BaseRequestHandler

class ClientData(object):
    def __init__(self, address, request, manager, request_function, queue_function):
        # This queue will be used by the connection request handler to queue up
        # received messages
        self.message_queue =  manager.Queue()

        # Start a process to handle the new socket connection
        self.handling_process = multiprocessing.Process(target=request_function,
                                                        args=(request, address, self.message_queue))
        self.handling_process.start()

        # Start a thread to process the queued messages
        self.queue_thread = threading.Thread(target=queue_function, args=(address, ))
        self.queue_thread.start()

        self.messages = []

class Handler(BaseRequestHandler):
    def __init__(self, request, client_address, server, message_queue):
        self.log = server.log
        self.message_queue = message_queue
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
        self.message_queue.put(message)

class MultiprocessMixin:
    def request_process(self, request, client_address, message_queue):
        try:
            self.finish_request(request, client_address, message_queue)
            self.shutdown_request(request)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        self.clients[client_address] = ClientData(address=client_address,
                                                  request=request,
                                                  manager=self.manager,
                                                  request_function=self.request_process,
                                                  queue_function=self.watch_queue)

class Server(MultiprocessMixin, TCPServer):
    allow_reuse_address = True

    def __init__(self, log_level, server_address, RequestHandlerClass):
        TCPServer.__init__(self,
                           server_address=server_address,
                           RequestHandlerClass=RequestHandlerClass)
        self.manager = multiprocessing.Manager()
        self.log = configure_logging(log_level, 'Server')

        self.clients = {}

    def finish_request(self, request, client_address, message_queue):
        self.RequestHandlerClass(request, client_address, self, message_queue)

    def watch_queue(self, client_address):
        message_dispatch = { 'HEARTBEAT'    : self.handle_aggregate_response,
                             'START'        : self.handle_start,
                             'STOP'         : self.handle_stop,
                             'ROLLOVER'     : self.handle_rollover,
                             'MONITOR'      : self.handle_monitor,
                             'MONITOR_ERROR': self.handle_monitor }

        client = self.clients.get(client_address, None)
        if client is None:
            return # Shouldn't get here

        while True:
            message = client.message_queue.get()

            # Handle each type of message
            dispatch_string = message_dispatch[message.type](message)
            self.log.info("Received {} from client @ {}{}".format(message.type,
                                                                  client_address,
                                                                  dispatch_string))

            client.messages.append(message)

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
        return self.handle_aggregate_response(message)

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
                                                message.payload.etime)

        return '; {} monitoring {} {}'.format(monitor_name, child_process, data)
