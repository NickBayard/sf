'''Contains the shared defintion of the configure_logging function.'''

import logging
from logging.handlers import TimedRotatingFileHandler

def configure_logging(log_level, name):
    '''Creates a logging instance with a TimedRotatingFileHandler and
       a StreamHandler.

        Args:
            log_level: A string matching the logging level.
                (e.g. DEBUG, INFO, WARNING)
            name: The name of the logger to use.

        Returns:
            A configured logging logger instance.
    '''
    logger = logging.getLogger(name)

    log_level = getattr(logging, log_level.upper(), None)
    logger.setLevel(log_level)

    # This may be overkill, but the logging file will roll over to a new file
    # every day at midnight
    fh = TimedRotatingFileHandler('{}.log'.format(name), when='midnight')
    sh = logging.StreamHandler()

    fileFormatter = logging.Formatter('%(asctime)s[%(levelname)s]:%(message)s')
    streamFormatter = logging.Formatter('%(asctime)s:%(message)s')

    fh.setFormatter(fileFormatter)
    sh.setFormatter(streamFormatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger
