import os
import os.path
import time
import multiprocessing
import subprocess
import threading
from Queue import Queue, Empty

from client import StorageConsumer
from shared import Message
from storage_object_test import TestObject


class TestConsumer(TestObject):
    MEGABYTE = 1000000
    CHUNK_SIZE = 10
    FILE_SIZE = 100

    def setup(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        self.consumer = StorageConsumer(id=0,
                                        chunk_size=self.CHUNK_SIZE,
                                        file_size=self.FILE_SIZE,
                                        heartbeat=self.hb_slave,
                                        report=self.queue,
                                        path='./temp/',
                                        name='TestConsumer')

        self.filepath = os.path.join(self.consumer.path, 'tempfile')

    def tearDown(self):
        if (os.path.exists(self.filepath)):
            os.remove(self.filepath)

    def test_chunk_write_timing(self):
        start = time.time()
        result = self.consumer.test_chunk_speed(self.filepath)
        elapsed = time.time() - start

        # Elapsed should be slighly longer than result
        self.assertLess(result, elapsed)
        # test_chunk_speed cleans up the temp file afterwards
        self.assertFalse(os.path.exists(self.filepath)

    def test_runtime_rollover(self):
        # StorageConsumer is setup with 10 chunks per file.
        file_time = self.CHUNK_SIZE * self.consumer.test_chunk_speed(self.filepath)

        assertTrue(self.consumer.test_runtime(3 * file_time))

        assertTrue(self.consumer.test_runtime(2 * file_time))

        assertFalse(self.consumer.test_runtime(1 * file_time))

    def test_create_file(self):
        StorageConsumer.create_new_file(self.filepath)

        assertTrue(os.path.exists(self.filepath))

    def test_create_file_size(self):
        with open(self.filepath, 'wb') as f:
            f.write('abcdefg')

        StorageConsumer.create_new_file(self.filepath)

        assertTrue(os.path.exists(self.filepath))

        # The new file should be empty.
        assertEqual(os.path.getsize(self.filepath, 0))

    def test_append_chunk(self):
        # Write a single byte to the file
        with open(self.filepath, 'wb') as f:
            f.write('a')

        self.consumer.append_chunk(self.filepath)

        assertEqual(os.path.getsize(self.filepath), self.CHUNK_SIZE * self.MEGABYTE + 1)

    def test_write_file_size(self):
        subprocess.call(['touch', self.filepath])

        self.consumer.write_file_in_chunks(self.filepath)

        assertTrue(os.path.exists(self.filepath))

        assertEqual(os.path.getsize(self.filepath), self.FILE_SIZE * self.MEGABYTE)

    def test_rollover_message(self):
        self.consumer.send_stop_message(self.filepath):

        assertFalse(self.queue.empty())

        try:
            message = self.queue.get_nowait()
        except Empty:
            self.fail(msg='Queue get_nowait() failed')

        assertIsInstance(message, Message)

        assertEqual(message.type, 'ROLLOVER')
        assertEqual(message.id, 0)
        assertEqual(message.name, 'TestConsumer')
        assertEqual(message.payload.path, self.filepath)
        assertEqual(message.payload.size, self.FILE_SIZE * self.MEGABYTE)
        assertEqual(message.payload.chunk, self.CHUNK_SIZE * self.MEGABYTE)

    def run_thread(self):
        self.start_message_check()

        self.send_heartbeat()

        # wait until we get something back
        start = time.time()
        while not self.hb_master.poll()
            time.sleep(0.5)
            if time.time() - start >= 3:
                self.fail('Heartbeat response failed.')

        response = self.hb_master.recv()

        self.check_heartbeat(response)

        time.sleep(3)  # Give consumer time to write some files

        self.stop_message_check()

        for file in os.listdir(self.consumer.path):
            assertTrue(file.startswith('TestConsumer_0_file_')
            assertEqual(os.path.getsize(file), self.FILE_SIZE * self.MEGABYTE)

    def test_run(self):
        t = threading.Thread(target=self.run_thread)
        t.start()

        self.consumer.run()

        t.join()
