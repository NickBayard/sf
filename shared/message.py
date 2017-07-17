'''Contains the shared definition for the Message class.'''


class Message(object):
    '''The Message class is used as the vessel for objects sent between
       process and threads over sockets, pipes and queues.'''

    def __init__(self, name, date_time, type, payload=None, id=0):
        '''Initializes a Message with:

            Args:
                name: A string name of the sender.
                id: An integer index for objects that have multiple instances.
                date_time: None or a datetime object indicating the time sent.
                type: A string indicating the type of message sent.
                      NOTE: An enum would be less error prone, but would
                      require either installing enum34.
                payload: The message contents, which vary by type.
        '''
        self.name = name
        self.id = id
        self.date_time = date_time
        self.type = type
        self.payload = payload

    def __repr__(self):
        '''Provides a repr() implementation for Message.

            Returns:
                A repr string for Message.
        '''
        repr_string = '{}('.format(self.__class__.__name__)
        repr_string += 'date_time={}, '.format(self.date_time)
        repr_string += 'name={}, '.format(self.name)
        repr_string += 'id={}, '.format(self.id)
        repr_string += 'type={}, '.format(self.type)
        repr_string += 'payload={}'.format(repr(self.payload))
        repr_string += ')'
        return repr_string
