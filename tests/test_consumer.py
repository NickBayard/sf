import os
import os.path
import time
import multiprocessing
import subprocess
import math
from Queue import Queue

from client import StorageConsumer
from shared import Message
from test_storage_object import TestObject


class TestConsumer(TestObject):
    MEGABYTE = 1000000
    CHUNK_SIZE = 10
    FILE_SIZE = 100
    NAME = 'TestConsumer'

    def setUp(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        self.dut = StorageConsumer(id=0,
                                        chunk_size=self.CHUNK_SIZE,
                                        file_size=self.FILE_SIZE,
                                        heartbeat=self.hb_slave,
                                        report=self.queue,
                                        path='./temp/',
                                        name=self.NAME)

        self.filepath = os.path.join(self.dut.path, 'tempfile')

    def tearDown(self):
        if (os.path.exists(self.filepath)):
            os.remove(self.filepath)

    def test_chunk_write_timing(self):
        start = time.time()
        result = self.dut.test_chunk_speed(self.filepath)
        elapsed = time.time() - start

        # Elapsed should be slighly longer than result
        self.assertLess(result, elapsed)
        # test_chunk_speed cleans up the temp file afterwards
        self.assertFalse(os.path.exists(self.filepath))

    def test_runtime_rollover(self):
        # StorageConsumer is setup with 10 chunks per file.
        chunks_per_file = math.ceil(self.FILE_SIZE/self.CHUNK_SIZE)
        file_time =  chunks_per_file * self.dut.test_chunk_speed(self.filepath)

        self.assertTrue(self.dut.test_runtime(2 * file_time))

        self.assertFalse(self.dut.test_runtime(file_time / 2))

    def test_create_file(self):
        StorageConsumer.create_new_file(self.filepath)

        self.assertTrue(os.path.exists(self.filepath))

    def test_create_file_size(self):
        with open(self.filepath, 'wb') as f:
            f.write('abcdefg')

        StorageConsumer.create_new_file(self.filepath)

        self.assertTrue(os.path.exists(self.filepath))

        # The new file should be empty.
        self.assertEqual(os.path.getsize(self.filepath), 0)

    def test_append_chunk(self):
        # Write a single byte to the file
        with open(self.filepath, 'wb') as f:
            f.write('a')

        self.dut.append_chunk(self.filepath)

        self.assertEqual(os.path.getsize(self.filepath), self.CHUNK_SIZE * self.MEGABYTE + 1)

    def test_write_file_size(self):
        subprocess.call(['touch', self.filepath])

        self.dut.write_file_in_chunks(self.filepath)

        self.assertTrue(os.path.exists(self.filepath))

        self.assertEqual(os.path.getsize(self.filepath), self.FILE_SIZE * self.MEGABYTE)

    def test_rollover_message(self):
        with open(self.filepath, 'w') as f:
            f.write('abc')

        self.dut.send_rollover_message(self.filepath)

        self.assertFalse(self.queue.empty())

        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertIsInstance(message, Message)

        self.assertEqual(message.type, 'ROLLOVER')
        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, self.NAME)
        self.assertEqual(message.payload.path, self.filepath)
        self.assertEqual(message.payload.size, 3)
        self.assertEqual(message.payload.chunk, self.CHUNK_SIZE * self.MEGABYTE)

    def run_thread(self):
        self.start_message_check()

        self.send_heartbeat()

        # Give HB client 3 seconds to respond
        self.assertTrue(self.hb_master.poll(3))

        if self.hb_master.poll():
            response = self.hb_master.recv()
            self.check_heartbeat(response)

        time.sleep(3)  # Give consumer time to write some files

        self.send_heartbeat_kill()

        # Give consumer time to respond to kill signal and finish writing final file
        time.sleep(3)

        self.stop_message_check()

        file_basename = '{}_0_file_'.format(self.NAME)

        # Check that at least one file has been written.
        # 6 seconds should be enough to write a 100MB file
        self.assertTrue(os.path.exists(os.path.join(self.dut.path, '{}0'.format(file_basename))))

        for file in os.listdir(self.dut.path):
            # Check file naming
            self.assertTrue(file.startswith(file_basename))

            path = os.path.join(self.dut.path, file)
            # Check file size
            self.assertEqual(os.path.getsize(path), self.FILE_SIZE * self.MEGABYTE)

    def test_run(self):
        self.run_test()
