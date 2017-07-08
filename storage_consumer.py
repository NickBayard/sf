#! /usr/bin/env python2

'''Enter module docstring here'''

from __future__ import print_function
import os 
import os.path
import subprocess
import multiprocessing

class StorageConsumer(object):
    def __init__(self, chunk_size, file_size):
        self.name = multiprocessing.current_process().name
        self.chunk_size = chunk_size * 1000000
        self.file_size = file_size * 1000000
        print('{} pid {}'.format(self.name, multiprocessing.current_process().pid))

    def run(self):
        #file_num = 0
        #while True:  # TODO change to a kill event from master
        for file_num in range(1):
            filename = '{}_file_{}'.format(self.name, file_num)

            # Create the file first. We will need to close the file after each
            # write in order to get an accurate size measurement
            subprocess.call(['touch', filename])

            while os.path.getsize(filename) < self.file_size:
                with open(filename, 'ab') as f:
                    # Construct a byte string of chunk_size and then
                    # write to file
                    f.write(os.urandom(self.chunk_size))

            #file_num += 1
            #break  # TODO Go away after kill event is added

