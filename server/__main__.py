#! /usr/bin/env python2

'''Main entry point for running a Server directly via
    python -m server
'''

import sys
import os.path
import argparse

try:
    import yaml
except ImportError:
    sys.exit("PyYaml module not present.  Please run 'pip install pyyaml'")

from . import __version__
from .server import Server
from .handler import Handler
from .config import ServerConfig


def main(config):
    '''The main entry point when running a Server instance.'''

    # This server will bind to server_address and listen for connection
    # requests.  Each connection handler will be given its own process.
    server_address = (config.host, config.port)
    server = Server(log_level=config.log_level,
                    server_address=server_address,
                    RequestHandlerClass=Handler,
                    report_path=config.report_path)
    server.serve_forever()
    server.cleanup()

def update_config(config, args):
    '''Override ServerConfig with command line arguments when provided.

        Args:
            config: The ServerConfig instance.
            args: dict of command line arguments.

        Returns:
            Modifed ServerConfig overridden by command line arguments.
    '''
    config.port = args.port if args.port is not None else config.port

    config.log_level = args.log_level if args.log_level is not None \
        else config.log_level

def get_config(args):
    '''Imports a ServerConfig instance from the server configuration file.

        Args:
            args: dict of command line arguments.

        Returns:
            A ServerConfig instance.
    '''
    if not os.path.exists(args.config_path) or \
        not os.path.isfile(args.config_path):
        sys.exit('Path {} doesn\'t exist'.format(args.config_path))

    with open(args.config_path, 'r') as config_file:
        config =  yaml.load(config_file)

    # Command line arguments should override configuration file
    update_config(config, args)

    return config

def get_command_line_args():
    '''Sets up argparse arguments and parses the command line arguments.

        Returns:
            A dict of command line arguments.
    '''
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
    # Gather config file and command line arguments and sent to main()
    main(get_config(get_command_line_args()))
