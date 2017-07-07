#! /usr/bin/env python2

'''Enter module docstring here'''

import pdb
import sys
import os.path
import argparse
from multiprocessing import Process

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")

from client_config import ClientConfig
from storage_consumer import StorageConsumer

def storage_factory(config, id):
    storage = StorageConsumer(id, config.chunk_size)
    storage.run()

def main(config):
    processes = []
    for id in range(config.storage_count):
        p = Process(target=storage_factory, args=(config,id))
        processes.append(p)
        p.start()

def update_config(config, args):
    pass

def get_config(args):
    pdb.set_trace()
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

    parser.add_argument('-s', '--storage-processes', type=int,
        dest='storage_count', default=1,
        help='Number of worker processes to consume storage.')

    parser.add_argument('--config-file', dest='config_path',
        default='client_config.yaml',
        help='File path of yaml configuration file for client.')

    parser.add_argument('--default-chunk-size', type=int,
        dest='chunk_size', default=10,
        help='Default chunk size in MB for storage consumers.')

    parser.add_argument('-t', '--runtime', type=int, default=600,
        help='Time (sec) that client should run for.')

    return parser.parse_args()

if __name__ == 'main':
    main(get_config(get_command_line_args()))

