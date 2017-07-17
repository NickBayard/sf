'''Enter module docstring here'''

import yaml

class ServerConfig(yaml.YAMLObject):
    yaml_tag = u'!ServerConfig'

    def __init__(self,
                 host,
                 port,
                 report_path,
                 log_level):

        self.host = host
        self.port = port
        self.report_path = report_path
        self.log_level = log_level

    def __repr__(self):
        repr_string = '%s(' % (self.__class__.__name__)

        repr_string += 'host=%r, ' % (self.host)
        repr_string += 'port=%r, ' % (self.port)
        repr_string += 'report_path=%r, ' % (self.report_path)
        repr_string += 'log_level=%r, ' % (self.log_level)

        repr_string += ')'
        return  repr_string
