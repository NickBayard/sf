'''Enter module docstring here'''

import yaml

class ServerConfig(yaml.YAMLObject):
    yaml_tag = u'!ServerConfig'

    def __init__(self,
                 host,
                 port,
                 log_level):

        self.host = host
        self.port = port
        self.log_level = log_level

    def __repr__(self):
        repr_string = '%s(' % (self.__class__.__name__)

        repr_string += 'host=%r, ' % (self.host)
        repr_string += 'port=%r, ' % (self.port)
        repr_string += 'log_level=%r, ' % (self.log_level)

        repr_string += ')'
        return  repr_string
