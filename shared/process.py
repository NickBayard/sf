"""Contains the shared definition for the ProcessData class."""


class ProcessData(object):
    """A container housing a multiprocessing.Process and a
       multiprocessing.Pipe.
    """

    def __init__(self, process, pipe):
        """Initializes a ProcessData instance.

            Args:
                process: A multiprocessing.Process
                pipe: A multiprocessing.Pipe for communicating with process
        """
        self.process = process
        self.pipe = pipe


