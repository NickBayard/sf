'''Contains the definition for the StorageConsumer class.'''

import os
import os.path
import subprocess
from datetime import datetime
from collections import namedtuple

from process import StorageObject
from shared import Message, init_dir_path

class RolloverPayload(object):
    '''The RolloverPayload class is used as a container for the
       Message.payload sent to the Heartbeat process.  Though a
       namedtuple could be used here because the contents are no
       longer modified, this object needs to be pickled to be 
       forwarded to the server.
    '''

    def __init__(self, path, size, chunk):
        '''Initializes a RolloverPayload with:

            Args:
                path: The path of the recently completed file.
                size: The total file size.
                chunk: The chunk size used to write this file.
        '''
        self.path = path
        self.size = size
        self.chunk = chunk


class StorageConsumer(StorageObject):
    '''The StorageConsumer writes a series of files of a prescribed size
       until it is signalled to stop by the StorageHeartbeat instance.

       StorageConsumer inherits from StorageObject, which makes it a
       multiprocessing process.

       File roll over events are sent over the "report" queue.

       KILL messages received on the "heartbeat" pipe force the process
       to stop after completing the current file.
    '''

    def __init__(self, id, chunk_size, file_size, heartbeat, report,
                 name=None, path='.'):
        '''Initializes a StorageConsumer with:

            Args:
                id: An integer index for objects that have multiple instances.
                chunk_size: Files should be written in chunks of this size.
                file_size: Files should rollover after reaching this size.
                heartbeat: A Pipe used to communicate with its master process.
                report: A queue for sending status messages to its master.
                name: A string name of the process.
                path: Directory path that the files should be written to.
        '''
        super(StorageConsumer, self).__init__(id=id,
                                              heartbeat=heartbeat,
                                              report=report,
                                              name=name)
        # Chunk and file sizes are received in 10MB units
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000

        # Validate the directory path
        self.path = init_dir_path(path)

    def run(self):
        '''Overridden from StorageObject and multiprocessing.Process
        
           run() contains the task that will be run in this process.'''

        # Report that this consumer has started running
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='START',
                                payload=None))

        file_num = 0

        # Stop when we get a KILL message from StorageHeartbeat
        while self.check_heartbeat():
            filename = '{}_{}_file_{}'.format(self.name,self.id, file_num)
            filepath = os.path.join(self.path, filename)

            # If the file happens to exist already, delete it.  It's probably
            # left over from an old run.
            if os.path.exists(filepath):
                os.remove(filepath)

            # Create a new file. We will need to close the file after each
            # write in order to get an accurate size measurement.
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

        # Report that this consumer has stopped running
        self.heartbeat.send(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='STOP',
                                    payload=None))
