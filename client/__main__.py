#! /usr/bin/env python2

"""Main entry point for running a client directly via
    python -m client
"""

import sys
import os.path
import argparse
import multiprocessing
import socket
import time

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")

from . import __version__
from .config import ClientConfig
from consumer import StorageConsumer
from monitor import StorageMonitor
from heartbeat import StorageHeartbeat
from shared import init_dir_path


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


def main(config):
    """The main entry point when running a Client instance."""

    # Create a single-consumer (heartbeat), multiple-producer queue.
    # The storage consumers and storage monitor processes will send their start,
    # stop and status messages to be handled by the heartbeat instance.
    manager = multiprocessing.Manager()
    slave_queue = manager.Queue()
    consumers = []

    # We create a socket first so that we can poll if the server is ready.
    # This way the client doesn't start running with no available server.
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while True:
        try:
            client_socket.connect((config.host, config.host_port))
            break
        except socket.error:
            time.sleep(5)

    for id in xrange(config.storage_count):
        # Each storage consumer process will have its own pipe, which the
        # heartbeat instance will use to poll if the consumer is alive. The
        # consumer will then respond on the other end of the pipe.
        master, slave = multiprocessing.Pipe()

        consumer = ProcessData(
                        process=StorageConsumer(id=id,
                                                chunk_size=config.chunk_sizes[id],
                                                file_size=config.file_sizes[id],
                                                heartbeat=slave,
                                                report=slave_queue,
                                                name='Consumer',
                                                path=config.storage_path),
                        pipe=master)

        # We need to test the chunk_size/runtime limits before starting up
        temp_filepath = os.path.join(consumer.process.path, 'temp')
        if not StorageConsumer.test_runtime(runtime=config.runtime,
                                            path=temp_filepath,
                                            chunk_size=consumer.process.chunk_size,
                                            file_size=consumer.process.file_size):
            format_message = 'Runtime {} and chunk size {} for Consumer {}'.format(
                config.runtime, consumer.process.chunk_size, id)
            sys.exit('{} not sufficient for 2x rollover.'.format(format_message))

        consumers.append(consumer)

    # Don't start any processes running until all chunk_sizes can be validated
    for consumer in consumers:
        consumer.process.start()

    # Similar to the storage consumers, the monitor process will use this pipe
    # to commuicate with the heartbeat instance to indicate that it is alive.
    master, slave = multiprocessing.Pipe()

    monitor = ProcessData(
                process=StorageMonitor(processes=[c.process for c in consumers],
                                       id=0,  # Only one monitor instance
                                       heartbeat=slave,
                                       report=slave_queue,
                                       poll_period=config.monitor_poll_period,
                                       name='Monitor'),
                pipe=master)

    monitor.process.start()

    # Storage consumers and the storage monitor are seperate processes, but
    # the heartbeat is just a class running in this process.
    heartbeat = StorageHeartbeat(consumers=consumers,
                                 monitor=monitor,
                                 report_in=slave_queue,
                                 runtime=config.runtime,
                                 poll_period=config.heartbeat_poll_period,
                                 client_socket=client_socket,
                                 log_level=config.log_level)
    heartbeat.run()

    monitor.process.join()
    for consumer in consumers:
        consumer.process.join()

def update_config(config, args):
    """Override ClientConfig with command line arguments when provided.

        Args:
            config: The ClientConfig instance.
            args: dict of command line arguments.

        Returns:
            Modifed ClientConfig overridden by command line arguments.
    """
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
    """Imports a ClientConfig instance from the client configuration file.

        Args:
            args: dict of command line arguments.

        Returns:
            A ClientConfig instance.
    """
    if not os.path.exists(args.config_path) or \
        not os.path.isfile(args.config_path):
        sys.exit('Path {} doesn\'t exist'.format(args.config_path))

    with open(args.config_path, 'r') as config_file:
        config = yaml.load(config_file)

    # Command line arguments should override configuration file
    update_config(config, args)

    return config

def get_command_line_args():
    """Sets up argparse arguments and parses the command line arguments.

        Returns:
            A dict of command line arguments.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument('--config-file', dest='config_path',
        default='client_config.yaml',
        help='File path of yaml configuration file for client.')

    parser.add_argument('-s', '--storage-processes', type=int,
        dest='storage_count', metavar='COUNT',
        help='Number of worker processes to consume storage.')

    parser.add_argument('--default-chunk-size', type=int,
        dest='default_chunk_size', metavar='SIZE_MB',
        help="""Chunk size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.""")

    parser.add_argument('--default-file-size', type=int,
        dest='default_file_size', metavar='SIZE_MB',
        help="""File size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.""")

    parser.add_argument('-t', '--runtime', metavar= 'SECS', type=int,
        help='Time (sec) that client should run for.')

    parser.add_argument('-l', '--log-level', choices=['INFO', 'DEBUG'],
        dest='log_level',
        help='Default logging level.')

    parser.add_argument('-v', '--version', action='version',
        version='Storage Client v{}'.format(__version__))

    return parser.parse_args()

if __name__ == '__main__':
    # Gather config file and command line arguments and sent to main()
    main(get_config(get_command_line_args()))
