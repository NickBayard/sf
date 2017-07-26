""" Contains the unittest class and methods that test the StorageMonitor
    class.
"""

import os
import os.path
import time
import multiprocessing
from Queue import Queue
from copy import copy

from client import StorageMonitor, MonitorResponseError
from shared import Message
from test_storage_object import TestObject


class TestMonitor(TestObject):
    """The TestMonitor contains the unittests that are used for testing
       the StorageMonitor class.

       It is derived from TestObject with contains tests used for all
       StorageObject items.
    """

    class MockProcess:
        """ The MockProcess contains a limited subset of attribute of
            a multiprocessing.Process.
        """
        def __init__(self, id, pid, name):
            self.id = id
            self.pid = pid
            self.name = name

    NAME = 'TestMonitor'

    # StorageMonitor uses the 'ps' command to retreive process status.
    # This string mocks the response from the 'ps' command.
    RESPONSE = '%CPU %MEM ELAPSED\n 1.2  3.4    1000'.split(b'\n')

    def setUp(self):
        """ Set up a StorageMonitor instance at the beginning of each test.
            The StorageMonitor will be provided with a pipe for START and
            HEARTBEAT messages and a queue for MONITOR and STOP messages.
        """
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        # Tests will monitor 3 fake StorageConsumer processes
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
        """ Test the _monitor_error method.
            Verify that a correct Monitor Error is put on the queue.
        """
        self.dut._monitor_error(None)

        self.assertFalse(self.queue.empty())

        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertEqual(message.type, 'MONITOR_ERROR')
        self.common_message_check(message)

    def test_valid_response(self):
        """ Test the validate_monitor_response method.
            A known good 'ps' output string is validated.
        """
        try:
            cpu, mem, etime = self.dut.validate_monitor_response(self.RESPONSE)
        except MonitorResponseError:
            self.fail('MonitorResponseError')

        self.assertEqual(cpu, '1.2')
        self.assertEqual(mem, '3.4')
        self.assertEqual(etime, '1000')

    def test_invalid_response1(self):
        """ Test the validate_monitor_response method.
            A 'ps' output string with no header is validated.
        """
        response = self.RESPONSE[1:]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response2(self):
        """ Test the validate_monitor_response method.
            A 'ps' output string with only the header is validated.
        """
        response = self.RESPONSE[:1]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response3(self):
        """ Test the validate_monitor_response method.
            A 'ps' output string with no newline characters is validated.
        """
        response = [self.RESPONSE[0].strip()]
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response4(self):
        """ Test the validate_monitor_response method.
            A 'ps' output string with no etime value is validated.
        """
        response = copy(self.RESPONSE)
        response[1] = ' 1.2  3.4'
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def test_invalid_response5(self):
        """ Test the validate_monitor_response method.
            A 'ps' output string with an incorrect header is validated.
        """
        response = copy(self.RESPONSE)
        response[0] = 'error'
        self.assertRaises(MonitorResponseError, self.dut.validate_monitor_response, response)

    def check_monitor_message_common(self):
        """ A method that tests use to retreive MONITOR messages from the
            queue and validate them.
        """
        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertIsInstance(message, Message)
        self.assertEqual(message.type, 'MONITOR')
        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, self.NAME)

        return message.payload

    def test_monitor_message(self):
        """ Test the send_monitor_message method.
            Validate that the correct Message was generated
            and put on the queue for the heartbeat process.
        """
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
        """ Method used by tests to validate the payload contents
            of a MONITOR message.
        """
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
        """ Method used to check the queue from the monitor process and
            validate its contents.
        """
        self.assertFalse(self.queue.empty())

        while not self.queue.empty():
            self.validate_monitor_payload(self.check_monitor_message_common())

    def run_thread(self):
        """ A thread that is run along side the run() method.
            Sends the appropriate messages into the StorageMonitor
            and verify that the appropriate messages are put out.
        """
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
        """ Functional test to exercise the run() method.
            This function definition is in TestObject.
        """
        self.run_test()
