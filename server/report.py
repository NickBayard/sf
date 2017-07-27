"""Contains the definitions for the Report class"""

import os.path
import math

from datetime import datetime
from collections import namedtuple

from shared import init_dir_path


class Report(object):
    """ The Report class encapsulates the ability to generate a text report
        from the set of messages received by the server from the clients.
    """

    # This namedtuple is used when processing the messages in the report
    ID = namedtuple('ID', 'name id')

    def __init__(self, path, clients):
        """Initialize a Report with:

           Args:
            path: A directory path where the report should be placed.
            clients: A dict of ClientData values which houses a list
                of messages received from each client.
        """
        self.path = init_dir_path(path)
        self.clients = clients

    def generate(self):
        """Generate a report on all previously connected clients."""
        filename = 'Server_Report_{}.log'.format(datetime.now().strftime('%Y%m%d_%H%M%S'))
        filepath = os.path.join(self.path, filename)

        with open(filepath, 'w') as file:
            for address, client in self.clients.iteritems():
                file.write('Client @ {}:{}\n\n'.format(address[0], address[1]))

                self._report_runtime(file=file,
                                     starts=client.messages.get('START'),
                                     stops=client.messages.get('STOP'))

                self._report_heartbeat(file=file,
                                       messages=client.messages.get('HEARTBEAT'))

                self._report_rollover(file=file,
                                      messages=client.messages.get('ROLLOVER'))

                self._report_monitor(file=file,
                                     messages=client.messages.get('MONITOR'))

                file.write('\n')

    def _report_runtime(self, file, starts, stops):
        """Generate report text about the runtime of the client.
           This information is extracted from the set of start and
           stop messages.

           Args:
            file: An open file handle for outputting text to.
            starts: A list of start messages for a particular client.
            stops: A list of stop messages for a particular client.
        """

        class StartStop(object):
            def __init__(self, start=None, stop=None):
                self.start = start
                self.stop = stop

        file.write('  Runtime:\n')
        # Verify that we received a START and STOP message
        if starts is not None and stops is not None:
            # We should get a start and stop message from each client process
            # Build a dictionary containing start and stop messages from
            # each child process
            messages = {}
            for s in starts:
                process = self.ID(name=s.name, id=s.id)

                if process in messages:
                    file.write('    ERROR: Multiple START messages detected ')
                    file.write('for {}_{}\n'.format(process.name, process.id))
                else:
                    messages[process] = StartStop(start=s)

            # There should only be 1 stop message
            if len(stops) > 1:
                file.write('    ERROR: Multiple STOP messages detected ')
            else:
                stop_received = stops[0].payload[0]
                stop_missing = stops[0].payload[1]

                # Add START messages
                for s in stop_received:
                    process = self.ID(name=s.name, id=s.id)
                    if process in messages:
                        if messages[process].stop is None:
                            messages[process].stop = s
                        else:
                            file.write('    ERROR: Multiple STOP messages detected ')
                            file.write('for {}_{}\n'.format(process.name, process.id))
                    else:
                        file.write('   ERROR: STOP message present without START ')
                        file.write('for {}_{}\n'.format(process.name, process.id))
                        messages[process].stop = StartStop(stop=s)

                # Report on missing stop messages
                for s in stop_missing:
                    process = self.ID(name=s[0], id=s[1])
                    if process in messages:
                        file.write('    ERROR: START message present without STOP ')
                        file.write('for {}_{}\n'.format(process.name, process.id))
                    else:
                        file.write('    ERROR: START and STOP messages missing ')
                        file.write('for {}_{}\n'.format(process.name, process.id))

            # Iterate through the messages and print the start/stop/runtimes
            for process, message in messages.iteritems():
                if message.stop is None:
                    # If a START is present and a STOP is not, then skip it, we've
                    # already written an error.
                    continue

                file.write('    {}_{}:\n'.format(process.name, process.id))

                if message.start is not None:
                    file.write('      Start: {}\n'.format(message.start.date_time))

                if message.stop is not None:
                    file.write('      Stop: {}\n'.format(message.stop.date_time))

                if message.start is not None and message.stop is not None:
                    runtime = message.stop.date_time - message.start.date_time
                    file.write('      Runtime: {}\n'.format(runtime))

        elif starts is None:
            # Didn't get a start message
            file.write('    ERROR: START messages not received.\n')
        elif stops is None:
            # Didn't get a stop message
            file.write('    ERROR: STOP messages not received.\n')

    def _report_heartbeat(self, file, messages):
        """Generate report text about the heartbeat messages of the
           client.

           Args:
            file: An open file handle for outputting text to.
            messages: A list of heartbeat messages for a particular client.
        """
        # HEARTBEAT messages are aggregated
        # Let's regroup them by child process
        heartbeat_messages = {}

        for message in messages:
            for child_process in message.payload[0]:
                process = self.ID(name=child_process.name, id=child_process.id)
                heartbeat_messages.setdefault(process, []).append(child_process.date_time)

            # Append error string for missing heartbeat
            for name, id in message.payload[1]:
                process = self.ID(name=name, id=id)
                heartbeat_messages.setdefault(process, []).append('ERROR: Missing heartbeat')

        file.write('\n')
        file.write('  Heartbeat:\n')
        # Now iterate through heartbeat_messages which have heartbeat responses and
        # missed responses grouped by child process
        for process, heartbeats in heartbeat_messages.iteritems():
            file.write('    {}_{}:\n'.format(process.name, process.id))
            for heartbeat in heartbeats:
                file.write('      {}\n'.format(heartbeat))

    def _report_rollover(self, file, messages):
        """Generate report text about the rollover messages of the
           client.

           Args:
            file: An open file handle for outputting text to.
            messages: A list of rollover messages for a particular client.
        """
        MEGABYTE = 1000000
        # ROLLOVER messages are not aggregated.
        # Group them by child process
        rollover_messages = {}

        for message in messages:
            process = self.ID(name=message.name, id=message.id)
            rollover_messages.setdefault(process, []).append(message)

        file.write('\n')
        file.write('  Rollovers:\n')
        for process, rollovers in rollover_messages.iteritems():
            file.write('    {}_{}:\n'.format(process.name, process.id))
            for rollover in rollovers:
                # TODO reformat chunk and file size
                chunk = math.floor(rollover.payload.chunk / MEGABYTE)
                size = math.floor(rollover.payload.size / MEGABYTE)
                file.write('      {}: {}MB chunk/{}MB @ {}\n'.format(rollover.date_time,
                                                               chunk,
                                                               size,
                                                               rollover.payload.path))

    def _report_monitor(self, file, messages):
        """Generate report text about the monitor messages of the
           client.

           Args:
            file: An open file handle for outputting text to.
            messages: A list of monitor messages for a particular client.
        """
        # MONITOR messages are not aggregated.
        # Group them by child process
        monitor_messages = {}

        for message in messages:
            process = self.ID(name=message.name, id=message.id)
            monitor_messages.setdefault(process, []).append(message)

        file.write('\n')
        file.write('  Process Status:\n')
        for process, monitors in monitor_messages.iteritems():
            file.write('    {}_{}:\n'.format(process.name, process.id))
            for status in monitors:
                file.write('      {}: {}_{} '.format(status.date_time,
                                                     status.payload.name,
                                                     status.payload.id))
                file.write('{}% cpu  {}% mem  {}s runtime\n'.format(status.payload.cpu,
                                                                     status.payload.mem,
                                                                     status.payload.etime))
