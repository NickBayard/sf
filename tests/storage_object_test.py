import unittest

from client import StorageObject
from shared import Message

class TestObject(unittest.TestCase):
    def setup(self):
        self.hb_master, self.hb_slave = multiprocessing.Pipe()
        self.queue = Queue()

        self.object = StorageObject(id=0,
                                    hearbeat=self.hb_slave,
                                    report=self.queue,
                                    name='TestObject')

    def common_message_check(self, message):
        assertIsInstance(message, Message)

        assertEqual(message.id, 0)
        assertEqual(message.name, 'TestObject')
        assertIsNone(message.payload)

    def test_start_message(self):
        self.object.send_start_message()

        assertFalse(self.queue.empty())

        try:
            message = self.queue.get_nowait()
        except Empty:
            self.fail(msg='Queue get_nowait() failed')

        assertEqual(message.type, 'START')
        self.common_message_check(message)

    def test_stop_message(self):
        self.object.send_stop_message()

        assertTrue(self.hb_master.poll())

        message = self.hb_master.recv()

        assertEqual(message.type, 'STOP')
        self.common_message_check(message)

    def test_check_heartbeat_none(self):
        assertTrue(self.object.check_heartbeat())

    def test_check_heartbeat_kill(self):
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='KILL',
                            payload=None)
        self.hb_master.send(message)
        assertFalse(self.object.check_heartbeat())

    def test_check_heartbeat_response(self):
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='HEARTBEAT',
                            payload=None)
        self.hb_master.send(message)

        assertTrue(self.object.check_heartbeat())

        assertTrue(self.hb_master.poll())

        response = self.hb_master.recv()

        assertEqual(response.type, 'HEARTBEAT')
        self.common_message_check(response)

    def test_run(self):
        assertRaises(NotImplementedError, self.object.run())

