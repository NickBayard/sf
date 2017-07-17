'''Contains the definition for the StorageMonitor class.'''

import os
import time
import subprocess
import re
import math
from datetime import datetime

from process import StorageObject
from shared import Message


class MonitorData(object):
    '''MonitorData is a container for processes that are monitored by
       StorageMonitor.  It is designed to be pickled and send as a
       Message payload.
    '''

    def __init__(self, process):
        '''Initializes a MonitorData with:

            Args:
                process: A multiprocessing.Process instance
        '''
        self.id = process.id
        self.pid = process.pid
        self.name = process.name

        # These will be populated later as the monitor runs
        self.cpu = None
        self.mem = None
        self.etime = None

    def __repr__(self):
        '''Provides a repr() implementation for MonitorData.
            
            Returns:
                A repr string for MonitorData.
        '''
        repr_string = '{}('.format(self.__class__.__name__)
        repr_string += 'id={}, '.format(self.id)
        repr_string += 'pid={}, '.format(self.pid)
        repr_string += 'name={}, '.format(self.name)
        repr_string += 'cpu={}, '.format(self.cpu)
        repr_string += 'mem={}, '.format(self.mem)
        repr_string += 'etime={}'.format(self.etime)
        repr_string += ')'
        return repr_string

class StorageMonitor(StorageObject):
    '''The StorageMonitor periodically polls some status information
       from one or more StorageConsumer instances on this client.

       StorageMonitor inherits from StorageObject, which makes it a
       multiprocessing process.

       Monitoring events are sent over the "report" queue.

       KILL messages received on the "heartbeat" pipe force the process
       to stop. These messages are polled once per second.
    '''

    def __init__(self, processes, id, heartbeat, report, poll_period, name=None):
        '''Initializes a StorageMonitor with:

            Args:
                processes: An interable of multiprocessing.Process objects
                id: An integer index for objects that have multiple instances.
                heartbeat: A Pipe used to communicate with its master process.
                report: A queue for sending status messages to its master.
                poll_period: Interval (s) on which StorageMonitor should poll
                    the StorageConsumers for their status information.
                name: A string name of the process.
        '''
        super(StorageMonitor, self).__init__(id=id,
                                             heartbeat=heartbeat,
                                             report=report,
                                             name=name)
        self.processes = [MonitorData(p) for p in processes]
        self.poll_period = poll_period

    def _monitor_error(self, process):
        '''Called whenever the monitor incounters an error retrieving the
           status of a consumer process. Sends a message to StorageHeartbeat
           indcating the error.
           
            Args:
                process: The MonitorData object of the process that caused
                    the error.
        '''
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='MONITOR_ERROR',
                                payload=process))

    def run(self):
        '''Overridden from StorageObject and multiprocessing.Process
        
           run() contains the task that will be run in this process.'''

        # Report that this monitor has started running
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='START',
                                payload=None))

        # Stop when we get a KILL message from StorageHeartbeat
        while self.check_heartbeat():
            monitor_start = time.time()

            for process in self.processes:
                # Use 'ps' to gather the cpu, memory, and runtime information
                command = ['ps', '-p', str(process.pid), '-o', 'pcpu,pmem,etimes']
                try:
                    response = subprocess.check_output(command).split(b'\n')
                except CalledProcessError:
                    self._monitor_error(process)
                    break

                # Check the first line of the response for 'CPU' and 'MEM'
                # to ensure that ps returned valid output
                match = re.search('CPU.+MEM', response[0])
                if match is None:
                    self._monitor_error(process)
                    break

                response_items = response[1].split()
                if not len(response_items) == 3:
                    self._monitor_error(process)
                    break

                process.cpu, process.mem, process.etime = response_items

                # Send the status information for this consumer to the 
                # StorageHeartbeat
                self.report.put(Message(name=self.name,
                                        id=self.id,
                                        date_time=datetime.now(),
                                        type='MONITOR',
                                        payload=process))

            # Subtract the elapsed time from the poll period for more accurate
            # monitor polling intervals
            sleep_time = self.poll_period - (time.time() - monitor_start)

            if sleep_time > 0:
                # Check for the heartbeat or kill message before sleeping
                if not self.check_heartbeat():
                    break

                # Sleep check the heartbeat in 1 second intervals
                # First sleep the remaining fraction
                time.sleep(sleep_time - math.floor(sleep_time))

                # We need this so that we can break out of the for/range loop
                # and then break out of the while loop again
                alive = True

                for _ in range(int(math.floor(sleep_time))):
                    if not self.check_heartbeat():
                        alive = False
                        break
                    time.sleep(1)

                if not alive:
                    break

        # Report that monitor has stopped running
        self.heartbeat.send(Message(name=self.name,
                                    id=self.id,
                                    date_time=datetime.now(),
                                    type='STOP',
                                    payload=None))
