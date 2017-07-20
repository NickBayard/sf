"""Contains the definition for the StorageObject class."""

import multiprocessing
from datetime import datetime

from shared import Message

class StorageObject(multiprocessing.Process):
    """The StorageObject is a multiprocessing.Process which gets instanciated
       in the children of the main client process.  It is an abstract class
       that must be inherited from."""

    def __init__(self, id, heartbeat, report, name=None):
        """Initializes StorageObject with:

            Args:
                id: An integer index for objects that have multiple instances.
                heartbeat: A Pipe used to communicate with its master process.
                report: A queue for sending status messages to its master.
                name: A string name of the process.
        """
        super(StorageObject, self).__init__(name=name)
        self.id = id
        self.heartbeat = heartbeat
        self.report = report

    def send_start_message(self):
        # Report that this process has started running
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='START',
                                payload=None))

    def send_stop_message(self):
        # Report that this process has stopped running
        self.heartbeat.send(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='STOP',
                                    payload=None))

    def check_heartbeat(self):
        """Checks the heartbeat pipe for a heartbeat request and replies
           if so.

            Returns:
                False if a kill message was received signalling process
                    to finish up.
                True in all other instances.
        """
        if self.heartbeat.poll():
            message = self.heartbeat.recv()

            if message.type == 'KILL':
                return False

            if message.type == 'HEARTBEAT':
                self.heartbeat.send(Message(name=self.name,
                                            id=0,
                                            date_time=datetime.now(),
                                            type='HEARTBEAT',
                                            payload=None))

        return True

    def run(self):
        """Abstract run method that must be overridden by a child class."""
        raise NotImplementedError
