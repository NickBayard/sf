"""Contains the definitions for the Server class"""

import pdb
import os.path
import threading
import multiprocessing

from Queue import Queue, Empty
from datetime import datetime
from collections import namedtuple

from shared import configure_logging, init_dir_path
from SocketServer import TCPServer
from handler import Handler

class ClientData(object):
    """A ClientData acts as a container of all client connection specific data.

       The Server instance has a clients dict, which has ClientData objects as
       its values and client addresses as its keys.

        Attributes:
            handling_process: Process for handling the connection request
                and receiving data over the socket.

            queue_thread: Thread that processes completed Messages from
                the handling_process.

            message_queue: A "managed" queue for the handling_process
                to forward Messages back to the queue_thread.

            messages: A dict of messages that have been processed by
                queue_thread. The dict is keyed by message type.

            kill: A "managed" Event that lets the server stop processes
                and threads from running.

            done: A flag indicating if the handling_process and
                queue_thread are running.
    """

    def __init__(self, address, request, manager, request_function, queue_function):
        """Initializes a ClientData with:

            Args:
                address: The client address tuple.
                request: The request socket connection.
                manager: A multiprocesses manager for creating inter-process
                    shared objects.
                request_function: The function that should handle the request.
                    This gets set as the target of the handling_process.
                queue_function: The function that should process completed
                    messages that were received on the socket. This gets
                    set as the target of the queue_thread.
        """
        # This queue will be used by the connection request handler to queue up
        # received messages.
        self.message_queue = manager.Queue()

        # This event will be used to stop running processes and threads for
        # this connection.
        self.kill = manager.Event()

        # Start a process to handle the new socket connection.
        self.handling_process = multiprocessing.Process(target=request_function,
                                                        args=(request, address, self.message_queue))
        self.handling_process.start()

        # Start a thread to process the queued messages.
        self.queue_thread = threading.Thread(target=queue_function, args=(address, ))
        self.queue_thread.start()

        # Messages processed by queue_thread will be stored here.
        self.messages = {}

        # Track the status of each client connection
        self.done = False


class MultiprocessMixin:
    """Similar to SocketServer ThreadingMixIn and ForkingMixin but uses
       multiprocessing.Process rather than os.fork(). This allows us to
       use a multiprocessing.Manager to share Events,Queues,etc with the
       child process.
    """
    def request_process(self, request, client_address, message_queue):
        """Overrides TCPServer.request_process in order to pass the
           message_queue to the handler.

           This function gets run on a new process to handle the connetion
           request.

            Args:
                request: A socket request object.
                client_address: A tuple containing the client ip/port.
                message_queue: A managed queue for loading Messages
                    received from on the socket.
        """
        try:
            self.finish_request(request, client_address, message_queue)
            self.shutdown_request(request)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Overrides TCPServer.process_request
           ForkingMixIn and ThreadingMixIn must also override this to produce
           an asynchronous object to handle the request.

            Args:
                request: A socket request object.
                client_address: A tuple containing the client ip/port.
        """
        # Each client connection gets its own ClientData
        # We should never get multiple requests from the same client address
        self.clients[client_address] = ClientData(address=client_address,
                                                  request=request,
                                                  manager=self.manager,
                                                  request_function=self.request_process,
                                                  queue_function=self.watch_queue)

    def finish_request(self, request, client_address, message_queue):
        """Creates a BaseHandlerClass instance that handles the request.

           Overrides BaseServer.finish_request in order to overload the
           RequestHandlerClass instantiation.

            Args:
                request: A socket request object.
                client_address: A tuple containing the client ip/port.
                message_queue: A managed queue for loading Messages
                    received from on the socket.
        """
        self.RequestHandlerClass(request, client_address, self, message_queue)


class Server(MultiprocessMixin, TCPServer):
    """Server acts as a SoceketServer.TCPServer that handles client connection
       requests as a separate multiprocessing.Process.

       Each client connection is assigned its own ClientData object.

       Attributes:
        clients: A dict with client address tuples as keys and ClientData
            as values.
    """

    # This namedtuple is used when processing the messages in the report
    ID = namedtuple('ID', 'name id')

    allow_reuse_address = True

    def __init__(self, log_level, server_address, RequestHandlerClass, report_path):
        """Initialize a Server with:

            Args:
                log_level: A string matching the logging level.
                    (e.g. DEBUG, INFO, WARNING)
                server_address: Address/port that this server will listen on.
                RequestHandlerClass: Class that handles socket requests
                report_path: Directory where server report should be placced.
        """
        # TCPServer/BaseServer are not new style classes and cannot use super()
        TCPServer.__init__(self,
                           server_address=server_address,
                           RequestHandlerClass=RequestHandlerClass)

        self.manager = multiprocessing.Manager()
        self.log = configure_logging(log_level, 'Server')

        self.clients = {}  # keys: (client ip,client port), values: ClientData

        # To map handling of various message types
        self.message_dispatch = { 'HEARTBEAT'    : self._handle_aggregate_response,
                                  'START'        : self._handle_start,
                                  'STOP'         : self._handle_stop,
                                  'ROLLOVER'     : self._handle_rollover,
                                  'MONITOR'      : self._handle_monitor,
                                  'MONITOR_ERROR': self._handle_monitor }

        self.report_path = init_dir_path(report_path)

    def cleanup(self):
        """Provide an opportunity to join processes and threads."""
        for client in self.clients.itervalues():
            #client.handling_process.join()
            client.queue_thread.join()

    def watch_queue(self, client_address):
        """Thread that processes Messages in the queue from the Handler.
           Also shuts down the socket and Handler process and generates the
           Server report when all clients are done.

            Args:
                client_address: Tuple of (client ip, client port)
        """
        client = self.clients.get(client_address, None)
        if client is None:
            return # Shouldn't get here

        while not client.kill.is_set():
            try:
                message = client.message_queue.get(timeout=2)
            except Empty:
                continue

            self._handle_message(message, client, client_address)

        # Kill event received.  Clean out the queue and stop.
        while not client.message_queue.empty():
            try:
                message = client.message_queue.get(block=False)
            except Empty:
                break # We shouldn't ever get here

            self._handle_message(message, client, client_address)

        self.shutdown() # Stop the serve_forever loop
        client.handling_process.join()

        client.done = True

        # If all clients are marked done, then this is the last thread to finish
        if self._are_all_clients_done():
            self._generate_report()

    def _handle_message(self, message, client, client_address):
        """Log each received message and put it into the client.messages list.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address
                client_address: A tuple of (client ip, client port)
        """
        dispatch_string = self.message_dispatch[message.type](message, client)
        self.log.info("Received {} from client @ {}{}".format(message.type,
                                                              client_address,
                                                              dispatch_string))

        client.messages.setdefault(message.type, []).append(message)

    def _handle_aggregate_response(self, message, client):
        """Generate a response string for Messages that have payloads with
           aggregated Messages in the payload.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address

            Returns:
                A string containing the client process name and id of each
                of the processes that did not respond to this aggregated
                message.
        """
        no_response_string = ''

        # payload[1] contains the set of non-responsive client processes
        if len(message.payload[1]):
            nonresponding = ['{}_{}'.format(process[0], process[1])
                                  for process in message.payload[1]]
            no_response_string = '; Child processes did not respond: {}'.format(
                ', '.join(nonresponding))

        return no_response_string

    def _handle_stop(self, message, client):
        """Generate a response string for STOP Messages and kills the current
           ClientData object.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address

            Returns:
                A string with the stop payload information.
        """
        # The client is stopping.  Need to close request handling process, queue
        # handling thread and socket
        client.kill.set()
        return self._handle_aggregate_response(message, client)

    def _handle_start(self, message, client):
        """Generate a response string for START Messages.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address

            Returns:
                An empty string.
        """
        return ''

    def _handle_rollover(self, message, client):
        """Generate a response string for ROLLOVER Messages.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address

            Returns:
                A string with the rollover payload information.
        """
        return '; {}_{} {}MB/{}MB chunks - {}'.format(message.name,
                                                  message.id,
                                                  message.payload.size / int(1e6),
                                                  message.payload.chunk / int(1e6),
                                                  message.payload.path)

    def _handle_monitor(self, message, client):
        """Generate a response string for MONITOR Messages.

            Args:
                message: A Message received from the client.
                client: A ClientData mapped to client_address

            Returns:
                A string with the monitor status information.
                MONITOR_ERROR messages return an empty string.
        """
        if message.payload is None:
            return ''

        # Building the string for readability
        monitor_name = '{}_{}'.format(message.name, message.id)
        child_process = '{}_{}: pid {},'.format(message.payload.name,
                                                 message.payload.id,
                                                 message.payload.pid)
        data = 'mem {}, cpu {}, time {}'.format(message.payload.mem,
                                                message.payload.cpu,
                                                message.payload.etime)

        return '; {} monitoring {} {}'.format(monitor_name, child_process, data)

    def _are_all_clients_done(self):
        """Iterate through clients to determine if they are all done.

            Returns:
                False if any of the clients are not done else True
        """
        for client in self.clients.itervalues():
            if not client.done:
                return False

        return True

    def _report_runtime(self, file, starts, stops):

        class StartStop(object):
            def __init__(self, start=None, stop=None):
                self.start = start
                self.stop = stop

        file.write('  Runtime:\n')
        # Verify that we received a START and STOP message
        if starts is not None and stops is not None:
            # We should get a start and stop message from each client process
            # Build a dictionary containing start and stop messages from
            # each child process
            messages = {}
            for s in starts:
                process = self.ID(name=s.name, id=s.id)

                if process in messages:
                    file.write('    ERROR: Multiple START messages detected ')
                    file.write('for {}_{}\n'.format(process.name, process.id))
                else:
                    messages[process] = StartStop(start=s)

            # There should only be 1 stop message
            if len(stops) > 1:
                file.write('    ERROR: Multiple STOP messages detected ')
            else:
                stop_received = stops[0].payload[0]
                stop_missing = stops[0].payload[1]

                # Add START messages
                for s in stop_received:
                    process = self.ID(name=s.name, id=s.id)
                    if process in messages:
                        if messages[process].stop is None:
                            messages[process].stop = s
                        else:
                            file.write('    ERROR: Multiple STOP messages detected ')
                            file.write('for {}_{}\n'.format(process.name, process.id))
                    else:
                        file.write('   ERROR: STOP message present without START ')
                        file.write('for {}_{}\n'.format(process.name, process.id))
                        messages[process].stop = StartStop(stop=s)

                # Report on missing stop messages
                for s in stop_missing:
                    process = self.ID(name=s[0], id=s[1])
                    if process in messages:
                        file.write('    ERROR: START message present without STOP ')
                        file.write('for {}_{}\n'.format(process.name, process.id))
                    else:
                        file.write('    ERROR: START and STOP messages missing ')
                        file.write('for {}_{}\n'.format(process.name, process.id))

            # Iterate through the messages and print the start/stop/runtimes
            for process, message in messages:
                if message.stop is None:
                    # If a START is present and a STOP is not, then skip it, we've
                    # already written an error.
                    continue

                file.write('    {}_{}:\n'.format(process.name, process.id))

                if message.start is not None:
                    file.write('      Start: {}\n'.format(message.start.date_time))

                if message.stop is not None:
                    file.write('      Stop: {}\n'.format(message.stop.date_time))

                if message.start is not None and message.stop is not None:
                    runtime = message.stop.date_time - message.start.date_time
                    file.write('      Runime: {}\n\n'.format(runtime))

        elif starts is None:
            # Didn't get a start message
            file.write('    ERROR: START messages not received.\n')
        elif stops is None:
            # Didn't get a stop message
            file.write('    ERROR: STOP messages not received.\n')

    def _report_heartbeat(self, file, messages):
        # HEARTBEAT messages are aggregated
        # Let's regroup them by child process
        heartbeat_messages = {}

        for message in messages:
            for child_process in message.payload[0]:
                process = ID(name=child_process.name, id=child_process.id)
                heartbeat_messages.setdefault(process, []).append(child_process.date_time)

            # Append None for missing heartbeat
            for name, id in message.payload[1]:
                process = ID(name=name, id=id)
                heartbeat_messages.setdefault(process, []).append('ERROR: Missing heartbeat')

        file.write('\n')
        file.write('  Heartbeat:\n')
        # Now iterate through heartbeat_messages which have heartbeat responses and
        # missed responses grouped by child process
        for process, heartbeats in heartbeats.iteritems():
            file.write('    {}_{}:\n'.format(process.name, process.id))
            for heartbeat in heartbeats:
                file.write('      {}\n'.format(heartbeat))

    def _report_rollover(self, file, messages):
        pass

    def _report_monitor(self, file, messages):
        pass

    def _generate_report(self):
        """Generate a report on all previously connected clients."""
        filename = 'Server_Report_{}.log'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
        filepath = os.path.join(self.report_path, filename)

        with open(filepath, 'w') as file:
            for address, client in self.clients.iteritems():
                file.write('Client @ {}:{}\n\n'.format(address[0], address[1]))

                pdb.set_trace()
                self._report_runtime(file=file,
                                     starts=client.messages.get('START'),
                                     stops=client.messages.get('STOP'))

                self._report_heartbeat(file=file,
                                       messages=client.messages.get('HEARTBEAT'))

                self._report_rollover(file=file,
                                      messages=client.messages.get('ROLLOVER'))

                self._report_monitor(file=file,
                                     messages=client.messages.get('MONITOR'))

                file.write('\n')
