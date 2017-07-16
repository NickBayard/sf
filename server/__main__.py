#! /usr/bin/env python2

'''Enter module docstring here'''
from __future__ import print_function

import sys
import os.path
import argparse

from . import __version__
from .server import Server, Handler
from .config import ServerConfig

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")


def main(config):
    # This server will bind to all available interfaces on this machine and
    # listen on config.port for connection requests.  Each request will
    # be given its own handler process.
    server_address = (config.host, config.port)
    server = Server(config.log_level, server_address, Handler)
    server.serve_forever()

def update_config(config, args):
    config.port = args.port if args.port is not None else config.port

    config.log_level = args.log_level if args.log_level is not None \
        else config.log_level

def get_config(args):
    if not os.path.exists(args.config_path) or \
        not os.path.isfile(args.config_path):
        sys.exit('Path {} doesn\'t exist'.format(args.config_path))

    with open(args.config_path, 'r') as config_file:
        config =  yaml.load(config_file)

    # Command line arguments should override configuration file
    update_config(config, args)

    return config

def get_command_line_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('--config-file', dest='config_path',
        default='server_config.yaml',
        help='File path of yaml configuration file for server.')

    # TODO add host arg

    parser.add_argument('-p', '--port', type=int,
        help='Listening port for the server')

    parser.add_argument('-l', '--log-level', choices=['INFO', 'DEBUG'],
        dest='log_level',
        help='Default logging level.')

    parser.add_argument('-v', '--version', action='version',
        version='Storage Server v{}'.format(__version__))

    return parser.parse_args()

if __name__ == '__main__':
    main(get_config(get_command_line_args()))

