'''Enter module docstring here'''

import os
import time
import subprocess
import re
import math
from datetime import datetime

from storage_object import StorageObject
from process_containers import MonitorData, Message

class StorageMonitor(StorageObject):

    def __init__(self, processes, id, heartbeat, report, poll_period, name=None):
        super(StorageMonitor, self).__init__(id=id,
                                             heartbeat=heartbeat,
                                             report=report,
                                             name=name)
        self.processes = [MonitorData(p) for p in processes]
        self.poll_period = poll_period

    def monitor_error(self, process):
        self.report.put(Message(name=self.name,
                                id=self.id,
                                date_time=datetime.now(),
                                type='MONITOR_ERROR',
                                payload=process))

    def run(self):
        # Report that monitor has started running
        self.report.put(Message(name=self.name,
                                id=self.id,
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
                    self.monitor_error(process)
                    break

                # Check the first line of the response for 'CPU' and 'MEM'
                # to ensure that ps returned valid output
                match = re.search('CPU.+MEM', response[0])
                if match is None:
                    self.monitor_error(process)
                    break

                response_items = response[1].split()
                if not len(response_items) == 3:
                    self.monitor_error(process)
                    break

                process.cpu, process.mem, process.etime = response_items

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
