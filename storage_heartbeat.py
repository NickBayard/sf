#! /usr/bin/env python2

'''Enter module docstring here'''

from __future__ import print_function
import os 
import os.path
import multiprocessing

class StorageHeartbeat(object):
    def __init__(self, consumers, monitor_pipe, report_in):
        self.consumers = consumers
        self.monitor_pipe = monitor_pipe
        self.report_in = report_in

    def run(self):
        pass
