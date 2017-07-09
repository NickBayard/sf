#! /usr/bin/env python2

'''Enter module docstring here'''

from __future__ import print_function
import os 
import os.path
import time
import multiprocessing
import subprocess
import re

class StorageMonitor(multiprocessing.Process):
    STORAGE_CONSUMER_POLL_PERIOD = 10

    class ProcessData(object):
        def __init__(self, process):
            self.process = process
            self.pid = process.pid
            self.name = process.name


    def __init__(self, name, processes=[]):
        super(StorageMonitor, self).__init__(name=name)
        self.processes = [self.ProcessData(p) for p in processes]

    def run(self):
        print('Monitor pid {}'.format(self.pid))
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
                print('{} pid {} cpu {} mem {} time {}'.format(process.name,
                                                               process.pid,
                                                               process.cpu, 
                                                               process.mem, 
                                                               process.etime))
                time.sleep(STORAGE_CONSUMER_POLL_PERIOD)
