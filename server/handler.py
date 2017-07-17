import re
import cPickle as pickle
from SocketServer import BaseRequestHandler

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
