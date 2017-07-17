'''Enter module docstring here'''

import os
import os.path
import subprocess
from datetime import datetime
from collections import namedtuple

from process import StorageObject
from shared import Message, init_dir_path

class RolloverPayload(object):
    def __init__(self, path, size, chunk):
        self.path = path
        self.size = size
        self.chunk = chunk


class StorageConsumer(StorageObject):


    def __init__(self, id, chunk_size, file_size, heartbeat, report,
                 name=None, path='.'):
        super(StorageConsumer, self).__init__(id=id,
                                              heartbeat=heartbeat,
                                              report=report,
                                              name=name)
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000
        self.path = init_dir_path(path)

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
            filepath = os.path.join(self.path, filename)

            # If the file happens to exist already, delete it.  It's probably
            # left over from an old run
            if os.path.exists(filepath):
                os.remove(filepath)

            # Create a new file. We will need to close the file after each
            # write in order to get an accurate size measurement
            subprocess.call(['touch', filepath])

            while os.path.getsize(filepath) < self.file_size:
                with open(filepath, 'ab') as f:
                    # Construct a byte string of chunk_size and then
                    # write to file
                    f.write(os.urandom(self.chunk_size))

            # Finished writing file, send rollover message
            payload = RolloverPayload(path=filepath,
                                      size=os.path.getsize(filepath),
                                      chunk=self.chunk_size)

            self.report.put(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='ROLLOVER',
                                    payload=payload))

            file_num += 1

        # Report that this consumer had stopped running
        self.heartbeat.send(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='STOP',
                                    payload=None))
