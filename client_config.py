#! /usr/bin/env python2

'''Enter module docstring here'''

import yaml

class ClientConfig(yaml.YAMLObject):
    yaml_tag = u'!ClientConfig'
    
    def __init__(self, storage_count, default_size, chunk_sizes, runtime):
        self.storage_count = storage_count
        self.default_chunk_size = default_size
        self.chunk_sizes = chunk_sizes
        self.runtime = runtime

    def __repr__(self):
        return '%s(storage_count=%r, default_chunk_size=%r, chunk_sizes=%r, runtime=%r)' % (
            self.__class__.__name__, self.storage_count, self.default_chunk_size,
            self.chunk_sizes, self.runtime)
