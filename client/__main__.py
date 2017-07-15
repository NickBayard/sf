#! /usr/bin/env python2

'''Enter module docstring here'''

import sys
import os.path
import argparse
import multiprocessing

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")

from . import __version__
from config import ClientConfig
from consumer import StorageConsumer
from monitor import StorageMonitor
from heartbeat import StorageHeartbeat
from shared import ProcessData


def main(config):
    # Create a single consumer (heartbeat), multiple producer queue.
    # The storage consumers and storage monitor processes will send their start,
    # stop and status messages to be handled by the heartbeat instance.
    manager = multiprocessing.Manager()
    slave_queue = manager.Queue()
    consumers = []

    for id in xrange(config.storage_count):
        # Each storage consumer process will have its own pipe, which the
        # heartbeat instance will use to poll is the consumer is alive. The
        # consumer will then respond on the other end of the pipe.
        master, slave = multiprocessing.Pipe()

        consumer = ProcessData(
                        process=StorageConsumer(id=id,
                                                chunk_size=config.chunk_sizes[id],
                                                file_size=config.file_sizes[id],
                                                heartbeat=slave,
                                                report=slave_queue,
                                                name='Consumer'),
                        pipe=master)
        consumers.append(consumer)
        consumer.process.start()

    # Similar to the storage consumers, the monitor process will use this pipe
    # to commuicate with the heartbeat instance to indicate that it is alive.
    master, slave = multiprocessing.Pipe()

    monitor = StorageMonitor(processes=[c.process for c in consumers],
                             id=0,  # Only one monitor instance
                             heartbeat=slave,
                             report=slave_queue,
                             poll_period=config.monitor_poll_period,
                             name='Monitor')
    monitor.start()

    # Storage consumers and the storage monitor are seperate processes, but
    # the heartbeat is just a class running in this process.
    heartbeat = StorageHeartbeat(consumers=consumers,
                                 monitor=ProcessData(process=monitor,
                                                       pipe=master),
                                 report_in=slave_queue,
                                 runtime=config.runtime,
                                 poll_period=config.heartbeat_poll_period,
                                 server=(config.host,config.host_port),
                                 log_level=config.log_level)
    heartbeat.run()

    # FIXME
    monitor.join()
    for consumer in consumers:
        consumer.process.join()

def update_config(config, args):
    config.storage_count = args.storage_count if args.storage_count is not None \
        else config.storage_count

    config.default_chunk_size = args.default_chunk_size if \
        args.default_chunk_size is not None  else config.default_chunk_size

    config.default_file_size = args.default_file_size if \
        args.default_file_size is not None  else config.default_file_size

    # Chunk sizes for each storage consumer are individually configurable.
    if len(config.chunk_sizes) > config.storage_count:
        # There were extra chunk sizes specified.
        config.chunk_sizes = config.chunk_sizes[:config.storage_count]
    elif len(config.chunk_sizes) < config.storage_count:
        # Not enough chunk sizes.  Backfill with default
        config.chunk_sizes.extend([config.default_chunk_size] *
            (config.storage_count - len(config.chunk_sizes)))

    # File sizes for each storage consumer are individually configurable.
    if len(config.file_sizes) > config.storage_count:
        # There were extra file sizes specified.
        config.file_sizes = config.file_sizes[:config.storage_count]
    elif len(config.file_sizes) < config.storage_count:
        # Not enough file sizes.  Backfill with default
        config.file_sizes.extend([config.default_file_size] *
            (config.storage_count - len(config.file_sizes)))

    config.runtime = args.runtime if args.runtime is not None \
        else config.runtime

    config.log_level = args.log_level if args.log_level is not None \
        else config.log_level

def get_config(args):
    if not os.path.exists(args.config_path) or \
        not os.path.isfile(args.config_path):
        #TODO Send failure to server
        sys.exit('Path {} doesn\'t exist'.format(args.config_path))

    with open(args.config_path, 'r') as config_file:
        config =  yaml.load(config_file)

    # Command line arguments should override configuration file
    update_config(config, args)

    return config

def get_command_line_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--config-file', dest='config_path',
        default='client_config.yaml',
        help='File path of yaml configuration file for client.')

    parser.add_argument('-s', '--storage-processes', type=int,
        dest='storage_count', metavar='COUNT',
        help='Number of worker processes to consume storage.')

    parser.add_argument('--default-chunk-size', type=int,
        dest='default_chunk_size', metavar='SIZE_MB',
        help='''Chunk size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.''')

    parser.add_argument('--default-file-size', type=int,
        dest='default_file_size', metavar='SIZE_MB',
        help='''File size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.''')

    parser.add_argument('-t', '--runtime', metavar= 'SECS', type=int,
        help='Time (sec) that client should run for.')

    parser.add_argument('-l', '--log-level', choices=['INFO', 'DEBUG'],
        dest='log_level',
        help='Default logging level.')

    parser.add_argument('-v', '--version', action='version',
        version='Storage Client v{}'.format(__version__))

    return parser.parse_args()

if __name__ == '__main__':
    main(get_config(get_command_line_args()))

