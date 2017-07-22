import unittest
import multiprocessing

from Queue import Queue, Empty

from client import StorageObject
from shared import Message

class TestObject(unittest.TestCase):
    NAME = 'TestObject'

    def setUp(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        self.dut = StorageObject(id=0,
                                 heartbeat=self.hb_slave,
                                 report=self.queue,
                                 name=self.NAME)

    def common_message_check(self, message):
        self.assertIsInstance(message, Message)

        self.assertEqual(message.id, 0)
        self.assertEqual(message.name, self.NAME)
        self.assertIsNone(message.payload)

    def start_message_check(self):
        try:
            message = self.queue.get(block=True, timeout=3)
        except Empty:
            self.fail(msg='Queue get() failed empty')

        self.assertEqual(message.type, 'START')
        self.common_message_check(message)

    def stop_message_check(self):
        self.assertTrue(self.hb_master.poll(3))

        message = self.hb_master.recv()

        self.assertEqual(message.type, 'STOP')
        self.common_message_check(message)

    def test_start_message(self):
        self.dut.send_start_message()
        self.start_message_check()

    def test_stop_message(self):
        self.dut.send_stop_message()
        self.stop_message_check()

    def test_check_heartbeat_none(self):
        self.assertTrue(self.dut.check_heartbeat())

    def send_heartbeat_kill(self):
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='KILL',
                            payload=None)
        self.hb_master.send(message)

    def test_check_heartbeat_kill(self):
        self.send_heartbeat_kill()
        self.assertFalse(self.dut.check_heartbeat())

    def send_heartbeat(self):
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='HEARTBEAT',
                            payload=None)
        self.hb_master.send(message)

    def check_heartbeat(self, response):
        self.assertEqual(response.type, 'HEARTBEAT')
        self.common_message_check(response)

    def test_check_heartbeat_response(self):
        self.send_heartbeat()

        self.assertTrue(self.dut.check_heartbeat())

        self.assertTrue(self.hb_master.poll())

        response = self.hb_master.recv()

        self.check_heartbeat(response)

    def test_run(self):
        self.assertRaises(NotImplementedError, self.dut.run)
