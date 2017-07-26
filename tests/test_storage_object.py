""" Contains the unittest class and methods that test the StorageObject
    class.
"""

import unittest
import multiprocessing
import threading

from Queue import Queue, Empty

from client import StorageObject
from shared import Message

class TestObject(unittest.TestCase):
    """The TestConsumer contains the unittests that are used for testing
       the StorageConsumer class.

       It is derived from to test classes that dervice from StorageObject.
    """
    NAME = 'TestObject'

    def setUp(self):
        """ Set up a StorageObject instance at the beginning of each test.
            The StorageObject will be provided with a pipe for START and
            HEARTBEAT messages and a queue for status and STOP messages.
        """
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        self.dut = StorageObject(id=0,
                                 heartbeat=self.hb_slave,
                                 report=self.queue,
                                 name=self.NAME)

    def common_message_check(self, message):
        """ A method that tests use to validate Messages that use
            None as the payload.
        """
        self.assertIsInstance(message, Message)

        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, self.NAME)
        self.assertIsNone(message.payload)

    def get_message_from_queue(self):
        """ A method used to attempt to get a message from the queue. """
        message = None

        try:
            message = self.queue.get(block=True, timeout=3)
        except Empty:
            self.fail(msg='Queue get() failed empty')

        return message

    def start_message_check(self):
        """ A method used to retreive a START message from the queue
            and validate it.
        """
        message = self.get_message_from_queue()

        self.assertIsNotNone(message)
        self.assertEqual(message.type, 'START')
        self.common_message_check(message)

    def stop_message_check(self):
        """ A method used to retreive a STOP message from the queue
            and validate it.
        """
        self.assertTrue(self.hb_master.poll(3))

        message = self.hb_master.recv()

        self.assertEqual(message.type, 'STOP')
        self.common_message_check(message)

    def test_start_message(self):
        """ Test the send_start_message method. """
        self.dut.send_start_message()
        self.start_message_check()

    def test_stop_message(self):
        """ Test the send_stop_message method. """
        self.dut.send_stop_message()
        self.stop_message_check()

    def test_check_heartbeat_none(self):
        """ Test the check_heartbeat method when there
            is no pending HEARTBEAT or KILL messages.
        """
        self.assertTrue(self.dut.check_heartbeat())

    def send_heartbeat_kill(self):
        """ Method used by tests to send a KILL message to client
            child processes.
        """
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='KILL',
                            payload=None)
        self.hb_master.send(message)

    def test_check_heartbeat_kill(self):
        """ Test the check_heartbeat message response when a KILL
            message is in the Pipe.
        """
        self.send_heartbeat_kill()
        self.assertFalse(self.dut.check_heartbeat())

    def send_heartbeat(self):
        """ Method used by tests to send a HEARBEAT message to client
            child processes.
        """
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='HEARTBEAT',
                            payload=None)
        self.hb_master.send(message)

    def check_heartbeat(self, response):
        """ Method used to verify the response of a client child
            process to a HEARTBEAT message.
        """
        self.assertEqual(response.type, 'HEARTBEAT')
        self.common_message_check(response)

    def test_check_heartbeat_response(self):
        """ Test the check_heartbeat message response when a HEARBEAT
            message is in the Pipe.
        """
        self.send_heartbeat()

        self.assertTrue(self.dut.check_heartbeat())

        self.assertTrue(self.hb_master.poll())

        response = self.hb_master.recv()

        self.check_heartbeat(response)

    def run_test(self):
        """ Creates a thread to run along side the run() method.
            The thread is implemented in the child class.
            The thread is responsible for sending messages to
            the target class and receiving and validating the
            results posted by the target class.
        """
        t = threading.Thread(target=self.run_thread)
        t.start()

        self.dut.run()

        t.join()

    def test_run(self):
        """ Functional test to exercise the run() method.
            The StorageObject class is abstract and this method
            should be implemented by the child.
        """
        self.assertRaises(NotImplementedError, self.dut.run)
