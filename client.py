#! /usr/bin/env python2

'''Enter module docstring here'''

from __future__ import print_function
import sys
import os
import os.path
import argparse
import multiprocessing

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")

from client_config import ClientConfig
from storage_consumer import StorageConsumer
from storage_monitor import StorageMonitor

def main(config):
    print('main pid {}'.format(os.getpid()))
    consumers = []
    for id in xrange(config.storage_count):
        process_name = 'Storage_Consumer_{}'.format(id) 

        consumer = StorageConsumer(chunk_size=config.chunk_sizes[id],
                            file_size=config.file_sizes[id],
                            name=process_name)
        consumers.append(consumer)
        consumer.start()
    
    monitor = StorageMonitor(processes=consumers, name='Monitor')
    monitor.start()

    # FIXME
    monitor.join()
    for proc in processes:
        proc.join()



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

    # TODO One more of ^these guys^ and we need to refactor

    config.runtime = args.runtime if args.runtime is not None \
        else config.runtime

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
        dest='storage_count', 
        help='Number of worker processes to consume storage.')

    parser.add_argument('--default-chunk-size', type=int,
        dest='default_chunk_size', 
        help='''Chunk size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.''')

    parser.add_argument('--default-file-size', type=int,
        dest='default_file_size', 
        help='''File size in MB for storage consumers if sizes for all
                consumers are not specificed in --config-file.''')

    parser.add_argument('-t', '--runtime', type=int, 
        help='Time (sec) that client should run for.')

    return parser.parse_args()

if __name__ == '__main__':
    main(get_config(get_command_line_args()))

