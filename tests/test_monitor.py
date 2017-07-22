import os
import os.path
import time
import multiprocessing
import subprocess
import threading
from Queue import Queue, Empty

from client import StorageMonitor
from shared import Message
from test_storage_object import TestObject


class TestMonitor(TestObject):
    class MockProcess:
        def __init__(self, id, pid, name):
            self.id = id
            self.pid = pid
            self.name = name

    NAME = 'TestMonitor'

    def setUp(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        processes = []
        for id in xrange(3):
            processes.append(TestMonitor.MockProcess(id=id,
                                                     pid=1000+id,
                                                     name='TestProcess'))

        self.dut = StorageMonitor(processes=processes,
                                       id=0,
                                       heartbeat=self.hb_slave,
                                       report=self.queue,
                                       poll_period=1,
                                       name=self.NAME)


    def test_monitor_error(self):
        self.dut._monitor_error(None)

        self.assertFalse(self.queue.empty())

        try:
            message = self.queue.get_nowait()
        except Empty:
            self.fail(msg='Queue get_nowait() failed')

        self.assertEqual(message.type, 'MONITOR_ERROR')
        self.common_message_check(message)

    def test_validate_response(self):
        pass

    def test_monitor_message(self):
        pass

    #def run_thread(self):
        #self.start_message_check()

        #self.send_heartbeat()

        ## wait until we get something back
        #start = time.time()
        #while not self.hb_master.poll():
            #time.sleep(0.5)
            #if time.time() - start >= 3:
                #self.fail('Heartbeat response failed.')

        #response = self.hb_master.recv()

        #self.check_heartbeat(response)

        #time.sleep(3)  # Give consumer time to write some files

        #self.stop_message_check()

        #for file in os.listdir(self.consumer.path):
            #self.assertTrue(file.startswith('TestConsumer_0_file_')
            #self.assertEqual(os.path.getsize(file), self.FILE_SIZE * self.MEGABYTE)

    def test_run(self):
        pass
        #t = threading.Thread(target=self.run_thread)
        #t.start()

        #self.consumer.run()

        #t.join()
