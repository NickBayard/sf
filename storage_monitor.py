'''Enter module docstring here'''

from __future__ import print_function
import os
import os.path
import time
import multiprocessing
import subprocess
import re
from datetime import datetime

from storage_object import StorageObject
from process_containers import MonitorData, Message

class StorageMonitor(StorageObject):

    def __init__(self, processes, id, heartbeat, report, poll_period, name=None):
        super(StorageMonitor, self).__init__(id=id,
                                             heartbeat=heartbeat,
                                             report=report,
                                             name=name)
        self.processes = [self.MonitorData(p) for p in processes]
        self.poll_period = poll_period

    def run(self):
        # Report that monitor has started running
        self.report.put(Message(name='Monitor',
                                id=0,
                                date_time=datetime.now(),
                                type='START',
                                payload=None))

        while self.check_heartbeat():
            monitor_start = time.time()

            for process in self.processes:
                command = ['ps', '-p', str(process.pid), '-o', 'pcpu,pmem,etimes']
                try:
                    response = subprocess.check_output(command).split(b'\n')
                except CalledProcessError:
                    break # TODO

                # Check the first line of the response for 'CPU' and 'MEM'
                # to ensure that ps returned valid output
                match = re.search('CPU.+MEM', response[0])
                if match is None:
                    break

                response_items = response[1].split()
                if not len(response_items) == 3:
                    break

                process.cpu, process.mem, process.etime = response_items

                message = Message(name='Monitor',
                                    id=0,
                                    date_time=datetime.now(),
                                    message=process)

            # Check for the heartbeat or kill message before sleeping
            if not self.check_heartbeat():
                break

            # Subtract the elapsed time from the poll period for more accurate
            # monitor polling intervals
            sleep_time = self.poll_period - (time.time() - monitor_start)
            if sleep_time > 0:
                time.sleep(sleep_time)

        # Report that monitor has stopped running
        self.report.put(Message(name='Monitor',
                                id=0,
                                date_time=datetime.now(),
                                type='STOP',
                                payload=None))
