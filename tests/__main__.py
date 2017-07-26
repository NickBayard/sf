#! /usr/bin/env python2

"""Main entry point for server and client tests.  Run with:
    python -m tests
"""

import unittest

from test_heartbeat import TestHeartbeat
from test_consumer import TestConsumer
from test_monitor import TestMonitor
from test_storage_object import TestObject
from test_handler import TestHandler
from test_server import TestServer

if __name__ == '__main__':
    unittest.main()
