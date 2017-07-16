'''Enter module docstring here'''

import yaml

class ClientConfig(yaml.YAMLObject):
    yaml_tag = u'!ClientConfig'

    def __init__(self,
                 host,
                 host_port,
                 storage_path,
                 storage_count,
                 default_chunk_size,
                 default_file_size,
                 chunk_sizes,
                 file_sizes,
                 monitor_poll_period,
                 runtime,
                 log_level):

        self.host = host
        self.host_port = host_port
        self.storage_path = storage_path
        self.storage_count = storage_count
        self.default_chunk_size = default_size
        self.default_file_size = default_file_size
        self.chunk_sizes = chunk_sizes
        self.file_sizes = file_sizes
        self.monitor_poll_period = monitor_poll_period
        self.heartbeat_poll_period = heartbeat_poll_period
        self.runtime = runtime
        self.log_level = log_level

    def __repr__(self):
        repr_string = '%s(' % (self.__class__.__name__)

        repr_string += 'host=%r, ' % (self.host)
        repr_string += 'host_port=%r, ' % (self.host_port)
        repr_string += 'storage_path=%r, ' % (self.storage_path)
        repr_string += 'storage_count=%r, ' % (self.storage_count)
        repr_string += 'default_chunk_size=%r, ' % (self.default_chunk_size)
        repr_string += 'default_file_size=%r, ' % (self.default_file_size)
        repr_string += 'chunk_sizes=%r, ' % (self.chunk_sizes)
        repr_string += 'file_sizes=%r, ' % (self.file_sizes)
        repr_string += 'monitor_poll_period=%r, ' % (self.monitor_poll_period)
        repr_string += 'heartbeat_poll_period=%r, ' % (self.heartbeat_poll_period)
        repr_string += 'runtime=%r, ' % (self.runtime)
        repr_string += 'log_level=%r, ' % (self.log_level)

        repr_string += ')'
        return  repr_string
