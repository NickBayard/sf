'''Module docs'''

import logging
from logging.handlers import TimedRotatingFileHandler

def configure_logging(log_level, name):
    logger = logging.getLogger(name)

    log_level = getattr(logging, log_level.upper(), None)
    logger.setLevel(log_level)

    fh = TimedRotatingFileHandler('{}.log'.format(name), when='midnight')
    sh = logging.StreamHandler()

    fileFormatter = logging.Formatter('%(asctime)s[%(levelname)s]:%(message)s')
    streamFormatter = logging.Formatter('%(asctime)s:%(message)s')

    fh.setFormatter(fileFormatter)
    sh.setFormatter(streamFormatter)

    logger.addHandler(fh)
    logger.addHandler(sh)

    return logger
