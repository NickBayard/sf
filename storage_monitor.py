#! /usr/bin/env python2

'''Enter module docstring here'''

from __future__ import print_function
import os 
import os.path
import time
import multiprocessing
import subprocess
import re

class StorageMonitor(object):
    STORAGE_CONSUMER_POLL_PERIOD = 10

    class ProcessData(object):
        def __init__(self, process):
            self.process = process
            self.pid = process.pid
            self.name = process.name


    def __init__(self, processes=[]):
        self.name = multiprocessing.current_process().name
        self.processes = [self.ProcessData(p) for p in processes]
        print('Monitor pid {}'.format(multiprocessing.current_process().pid))


    def run(self):
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

                cpu, mem, etime = response_items
                print('{} pid {} cpu {} mem {} time {}'.format(process.name,
                                                               process.pid,
                                                               cpu, mem, etime))
                time.sleep(3)
