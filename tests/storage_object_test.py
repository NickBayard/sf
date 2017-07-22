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

    def common_message_check(self, message, name):
        assertIsInstance(message, Message)

        assertEqual(message.id, 0)
        assertEqual(message.name, name)
        assertIsNone(message.payload)

    def start_message_check(self):
        assertFalse(self.queue.empty())

        try:
            message = self.queue.get_nowait()
        except Empty:
            self.fail(msg='Queue get_nowait() failed')

        assertEqual(message.type, 'START')
        self.common_message_check(message, 'TestObject')

    def stop_message_check(self):
        assertTrue(self.hb_master.poll())

        message = self.hb_master.recv()

        assertEqual(message.type, 'STOP')
        self.common_message_check(message, 'TestObject')

    def test_start_message(self):
        self.object.send_start_message()
        self.start_message_check()

    def test_stop_message(self):
        self.object.send_stop_message()
        self.stop_message_check()

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

    def send_heartbeat(self):
        message = Message(name='Heartbeat',
                            id=0,
                            date_time=None,
                            type='HEARTBEAT',
                            payload=None)
        self.hb_master.send(message)

    def check_heartbeat(self, response):
        assertEqual(response.type, 'HEARTBEAT')
        self.common_message_check(response, 'TestObject')

    def test_check_heartbeat_response(self):
        self.send_heartbeat()

        assertTrue(self.object.check_heartbeat())

        assertTrue(self.hb_master.poll())

        response = self.hb_master.recv()

        self.check_heartbeat(response)

    def test_run(self):
        assertRaises(NotImplementedError, self.object.run())

