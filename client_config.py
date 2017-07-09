#! /usr/bin/env python2

'''Enter module docstring here'''

import yaml

class ClientConfig(yaml.YAMLObject):
    yaml_tag = u'!ClientConfig'
    
    def __init__(self, storage_count, default_chunk_size, default_file_size,
                 chunk_sizes, file_sizes, monitor_poll_period, runtime):

        self.storage_count = storage_count
        self.default_chunk_size = default_size
        self.default_file_size = default_file_size
        self.chunk_sizes = chunk_sizes
        self.file_sizes = file_sizes
        self.monitor_poll_period = monitor_poll_period
        self.runtime = runtime

    def __repr__(self):
        repr_string = '%s(' % (self.__class__.__name__)

        repr_string += 'storage_count=%r, ' % (self.storage_count)
        repr_string += 'default_chunk_size=%r, ' % (self.default_chunk_size)
        repr_string += 'default_file_size=%r, ' % (self.default_file_size)
        repr_string += 'chunk_sizes=%r, ' % (self.chunk_sizes)
        repr_string += 'file_sizes=%r, ' % (self.file_sizes)
        repr_string += 'monitor_poll_period=%r, ' % (self.monitor_poll_period)
        repr_string += 'runtime=%r, ' % (self.runtime)

        repr_string += ')' 
        return  repr_string
