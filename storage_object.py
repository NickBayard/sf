'''Enter module docstring here'''

import multiprocessing
from datetime import datetime

from process_containers import Message

class StorageObject(multiprocessing.Process):
    def __init__(self, id, heartbeat, report, name=None):
        super(StorageObject, self).__init__(name=name)
        self.id = id
        self.heartbeat = heartbeat
        self.report = report

    def check_heartbeat(self):
        if self.heartbeat.poll():
            message = self.heartbeat.recv()

            if message.type == 'KILL':
                return False

            if message.type == 'HEARTBEAT':
                self.heartbeat.send(Message(name=self.name,
                                            id=0,
                                            date_time=datetime.now(),
                                            type='HEARTBEAT',
                                            payload=None))

        return True

    def run(self):
        raise NotImplementedError
