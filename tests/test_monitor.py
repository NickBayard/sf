import os
import os.path
import time
import multiprocessing
import subprocess
import threading
from Queue import Queue, Empty
from copy import copy

from client import StorageMonitor, MonitorResponseError
from shared import Message
from test_storage_object import TestObject


class TestMonitor(TestObject):

    class MockProcess:
        def __init__(self, id, pid, name):
            self.id = id
            self.pid = pid
            self.name = name

    NAME = 'TestMonitor'
    RESPONSE = '%CPU %MEM ELAPSED\n 1.2  3.4    1000'.split(b'\n')

    def setUp(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        processes = []
        for id in xrange(3):
            processes.append(self.MockProcess(id=id,
                                              # Monitor will watch this process
                                              pid=os.getpid(),
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

        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertEqual(message.type, 'MONITOR_ERROR')
        self.common_message_check(message)

    def test_valid_response(self):
        try:
            cpu, mem, etime = self.dut.validate_monitor_response(self.RESPONSE)
        except MonitorResponseError:
            self.fail('MonitorResponseError')

        self.assertEqual(cpu, '1.2')
        self.assertEqual(mem, '3.4')
        self.assertEqual(etime, '1000')

    def test_invalid_response1(self):
        # No header
        response = self.RESPONSE[1:]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response2(self):
        # Header only
        response = self.RESPONSE[:1]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response3(self):
        # Header with no newline
        response = [self.RESPONSE[0].strip()]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response4(self):
        # Strip the running time off
        response = copy(self.RESPONSE)
        response[1] = ' 1.2  3.4'
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response5(self):
        # Invalid header
        response = copy(self.RESPONSE)
        response[0] = 'error'
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def check_monitor_message_common(self):
        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertIsInstance(message, Message)
        self.assertEqual(message.type, 'MONITOR')
        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, self.NAME)

        return message.payload

    def test_monitor_message(self):
        process = self.MockProcess(id=1, pid=2, name='TestProcess')
        process.cpu = '1.2'
        process.mem = '3.4'
        process.etime = '1000'

        self.dut.send_monitor_message(process)

        payload = self.check_monitor_message_common()

        self.assertEqual(payload.id, 1)
        self.assertEqual(payload.pid, 2)
        self.assertEqual(payload.name, 'TestProcess')
        self.assertEqual(payload.cpu, '1.2')
        self.assertEqual(payload.mem, '3.4')
        self.assertEqual(payload.etime, '1000')

    def validate_monitor_payload(self, payload):
        self.assertIn(payload.id, [0,1,2])
        self.assertEqual(payload.pid, os.getpid())
        self.assertEqual(payload.name, 'TestProcess')

        # We can't know in advance what the results from 'ps' were
        # but we can make some assumptions about what was packaged
        self.assertIsInstance(payload.cpu, str)
        self.assertIsInstance(payload.mem, str)
        self.assertIsInstance(payload.etime, str)

        try:
            _ = float(payload.cpu)
        except ValueError:
            self.fail('cpu failed cast to float')

        try:
            _ = float(payload.mem)
        except ValueError:
            self.fail('mem failed cast to float')

        try:
            _ = int(payload.etime)
        except ValueError:
            self.fail('etime failed cast to int')

    def check_monitor_queue(self):
        self.assertFalse(self.queue.empty())

        while not self.queue.empty():
            self.validate_monitor_payload(self.check_monitor_message_common())

    def run_thread(self):
        self.start_message_check()

        self.send_heartbeat()

        # Give monitor seconds to respond
        self.assertTrue(self.hb_master.poll(3))

        if self.hb_master.poll():
            response = self.hb_master.recv()
            self.check_heartbeat(response)

        time.sleep(2)  # Give monitor time to put status messages in the queue

        self.send_heartbeat_kill()

        # Give monitor time to respond to kill signal
        time.sleep(1)

        self.stop_message_check()

        self.check_monitor_queue()

    def test_run(self):
        self.run_test()
