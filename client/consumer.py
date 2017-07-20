"""Contains the definition for the StorageConsumer class."""

import os
import os.path
import time
import subprocess
import math
from datetime import datetime
from collections import namedtuple

from process import StorageObject
from shared import Message, init_dir_path

class RolloverPayload(object):
    """The RolloverPayload class is used as a container for the
       Message.payload sent to the Heartbeat process.  Though a
       namedtuple could be used here because the contents are no
       longer modified, this object needs to be pickled to be
       forwarded to the server.
    """

    def __init__(self, path, size, chunk):
        """Initializes a RolloverPayload with:

            Args:
                path: The path of the recently completed file.
                size: The total file size.
                chunk: The chunk size used to write this file.
        """
        self.path = path
        self.size = size
        self.chunk = chunk


class StorageConsumer(StorageObject):
    """The StorageConsumer writes a series of files of a prescribed size
       until it is signalled to stop by the StorageHeartbeat instance.

       StorageConsumer inherits from StorageObject, which makes it a
       multiprocessing process.

       File roll over events are sent over the "report" queue.

       KILL messages received on the "heartbeat" pipe force the process
       to stop after completing the current file.
    """

    def __init__(self, id, chunk_size, file_size, heartbeat, report,
                 name=None, path='.'):
        """Initializes a StorageConsumer with:

            Args:
                id: An integer index for objects that have multiple instances.
                chunk_size: Files should be written in chunks of this size.
                file_size: Files should rollover after reaching this size.
                heartbeat: A Pipe used to communicate with its master process.
                report: A queue for sending status messages to its master.
                name: A string name of the process.
                path: Directory path that the files should be written to.
        """
        super(StorageConsumer, self).__init__(id=id,
                                              heartbeat=heartbeat,
                                              report=report,
                                              name=name)
        # Chunk and file sizes are received in 10MB units
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000

        # Validate the directory path
        self.path = init_dir_path(path)

    @staticmethod
    def test_chunk_speed(chunk_size, filepath):
        """Test the time to write a single chunk.

            Args:
                chunk_size: Size of chunk to write.
                path: Path of the temporary file that will be created.

            Returns:
                Time (s) it took to write a chunk-sized file to path.
        """
        if os.path.exists(filepath):
            os.remove(filepath)

        start = time.time()

        with open(filepath, 'wb') as f:
            f.write(os.urandom(chunk_size))

        elapsed = time.time() - start

        if os.path.exists(filepath):
            os.remove(filepath)

        return elapsed

    @staticmethod
    def test_runtime(runtime, path, chunk_size, file_size):
        """Tests the number of files that can rollover in a given runtime by
        timing the write for a single chunk.

            Args:
                runtime: Time (s) that StorageConsumer would be run for.
                path: An expanded file path that should be created for
                    the test.
                chunk_size: Size of the chunk that should be written to path.
                file_size: StorageConsumer would write this file size. File
                    write time is extrapolated from chunk write time.
            Returns:
                True if we can rollover at least 2 times else False
        """
        chunk_time = StorageConsumer.test_chunk_speed(chunk_size, path)

        num_chunks_per_file = math.ceil(file_size / chunk_size)

        time_per_file = chunk_time * num_chunks_per_file

        num_files_in_runtime = math.ceil(runtime / time_per_file)

        return num_files_in_runtime >= 2.0

    @staticmethod
    def create_new_file(filepath):
        # If the file happens to exist already, delete it.  It's probably
        # left over from an old run.
        if os.path.exists(filepath):
            os.remove(filepath)

        # Create a new file. We will need to close the file after each
        # write in order to get an accurate size measurement.
        subprocess.call(['touch', filepath])

    @staticmethod
    def append_chunk(filepath, chunk):
        with open(filepath, 'ab') as f:
            # Construct a byte string of chunk_size and then
            # write to file
            f.write(os.urandom(chunk))

    @staticmethod
    def write_file_in_chunks(filepath, file_size, chunk_size):
        while os.path.getsize(filepath) < file_size:
            StorageConsumer.append_chunk(filepath, chunk_size)

    def send_rollover_message(self, filepath):
        payload = RolloverPayload(path=filepath,
                                  size=os.path.getsize(filepath),
                                  chunk=self.chunk_size)

        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='ROLLOVER',
                                payload=payload))

    def run(self):
        """Overridden from StorageObject and multiprocessing.Process

           run() contains the task that will be run in this process."""

        self.send_start_message()

        file_num = 0

        # Stop when we get a KILL message from StorageHeartbeat
        while self.check_heartbeat():
            filename = '{}_{}_file_{}'.format(self.name,self.id, file_num)
            filepath = os.path.join(self.path, filename)

            StorageConsumer.create_new_file(filepath)

            StorageConsumer.write_file_in_chunks(filepath, self.file_size, self.chunk_size)

            self.send_rollover_message(filepath)

            file_num += 1

        self.send_stop_message()

