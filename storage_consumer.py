'''Enter module docstring here'''

import os
import os.path
import subprocess
from datetime import datetime

from storage_object import StorageObject
from process_containers import Message

class StorageConsumer(StorageObject):
    def __init__(self, id, chunk_size, file_size, heartbeat, report, name=None):
        super(StorageConsumer, self).__init__(id=id,
                                              heartbeat=heartbeat,
                                              report=report,
                                              name=name)
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000

    def run(self):
        # Report that this consumer had started running
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='START',
                                payload=None))

        file_num = 0
        while self.check_heartbeat():
            filename = '{}_{}_file_{}'.format(self.name,self.id, file_num)

            # Create the file first. We will need to close the file after each
            # write in order to get an accurate size measurement
            subprocess.call(['touch', filename])

            while os.path.getsize(filename) < self.file_size:
                with open(filename, 'ab') as f:
                    # Construct a byte string of chunk_size and then
                    # write to file
                    f.write(os.urandom(self.chunk_size))

            # Finished writing file, send rollover message
            self.report.put(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='ROLLOVER',
                                    payload=filename))

            file_num += 1

        # Report that this consumer had stopped running
        self.heartbeat.send(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='STOP',
                                    payload=None))
