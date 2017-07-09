'''Enter module docstring here'''

from __future__ import print_function
import os
import os.path
import subprocess
import multiprocessing

from process_containers import Message

class StorageConsumer(multiprocessing.Process):
    def __init__(self, id, chunk_size, file_size, heartbeat, report_queue, name=None):
        super(StorageConsumer, self).__init__(name=name)
        self.id = id
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000
        self.heartbeat = heartbeat
        self.report = report_queue

    def run(self):
        # Report that this consumer had started running
        self.report.put(Message(name='Consumer',
                                id=self.id,
                                data_time=datetime.now(),
                                type='START',
                                payload=None))

        #file_num = 0
        #while True:  # TODO change to a kill event from master
        for file_num in range(1):
            filename = '{}_file_{}'.format(self.name, file_num)

            # Create the file first. We will need to close the file after each
            # write in order to get an accurate size measurement
            subprocess.call(['touch', filename])

            while os.path.getsize(filename) < self.file_size:
                with open(filename, 'ab') as f:
                    # Construct a byte string of chunk_size and then
                    # write to file
                    f.write(os.urandom(self.chunk_size))

            # Finished writing file, send rollover message
            self.report.put(Message(name='Consumer',
                                    id=self.id,
                                    data_time=datetime.now(),
                                    type='ROLLOVER',
                                    payload=filename)

            #file_num += 1
            #break  # TODO Go away after kill event is added

        # Report that this consumer had stopped running
        self.report.put(Message(name='Consumer',
                                id=self.id,
                                data_time=datetime.now(),
                                type='STOP',
                                payload=None))
