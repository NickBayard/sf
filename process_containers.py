'''Enter module docstring here'''

from collections import namedtuple

class HeartbeatData(object):

    def __init__(self, process, pipe):
        self.process = process
        self.pipe = pipe


class MonitorData(object):

    def __init__(self, process):
        self.process = process
        self.pid = process.pid
        self.name = process.name


Message = namedtuple('Message', 'name id date_time type payload')
