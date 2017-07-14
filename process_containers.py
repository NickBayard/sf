'''Enter module docstring here'''

class HeartbeatData(object):

    def __init__(self, process, pipe):
        self.process = process
        self.pipe = pipe


class MonitorData(object):

    def __init__(self, process):
        self.id = process.id
        self.pid = process.pid
        self.name = process.name
        self.cpu = None
        self.mem = None
        self.etime = None

    def __repr__(self):
        repr_string = '{}('.format(self.__class__.__name__)
        repr_string += 'id={}, '.format(self.id)
        repr_string += 'pid={}, '.format(self.pid)
        repr_string += 'name={}, '.format(self.name)
        repr_string += 'cpu={}, '.format(self.cpu)
        repr_string += 'mem={}, '.format(self.mem)
        repr_string += 'etime={}'.format(self.etime)
        repr_string += ')'
        return repr_string


class Message(object):

    def __init__(self, name, date_time, type, payload=None, id=0):
        self.name = name
        self.date_time = date_time
        self.type = type
        self.payload = payload
        self.id = id

    def __repr__(self):
        repr_string = '{}('.format(self.__class__.__name__)
        repr_string += 'date_time={}, '.format(self.date_time)
        repr_string += 'name={}, '.format(self.name)
        repr_string += 'id={}, '.format(self.id)
        repr_string += 'type={}, '.format(self.type)
        repr_string += 'payload={}'.format(repr(self.payload))
        repr_string += ')'
        return repr_string
