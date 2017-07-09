'''Enter module docstring here'''

from __future__ import print_function
import os
import os.path
import time
import multiprocessing
import subprocess
import re
from datetime import datetime

from process_containers import MonitorData, Message

class StorageMonitor(multiprocessing.Process):

    def __init__(self, processes, heartbeat, report_queue, poll_period, name=None):
        super(StorageMonitor, self).__init__(name=name)
        self.processes = [self.MonitorData(p) for p in processes]
        self.heartbeat = heartbeat
        self.report = report_queue
        self.poll_period = poll_period

    def run(self):
        # Report that monitor has started running
        self.report.put(Message(name='Monitor',
                                id=0,
                                data_time=datetime.now(),
                                type='START',
                                payload=None))

        while True:  # TODO Replace with kill event
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
                                    data_time=datetime.now(),
                                    message=process)

            time.sleep(self.poll_period)

        # Report that monitor has stopped running
        self.report.put(Message(name='Monitor',
                                id=0,
                                data_time=datetime.now(),
                                type='STOP',
                                payload=None))
