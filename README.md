# Solidfire/NetApp Programming Exercise

## TODO
    
1.  Better server report
2.  Unit Tests
3.  Document Tests

## General

The included application contains 3 modules:
*  Server
*  Client
*  Tests

## Installation

To run the server and client, one must install PyYaml.  This could be done using `pip`:
```
pip install pyyaml
```
To run the tests, mock must be installed.  This is also available on PyPi for Python 2:
```
pip install mock
```

For convenience, the included Makefile has a rule that will install both of these.
```
make install
```

## Running

The tests can be run very simply by running the module directly from Python:
```
python -m tests
```

or via make:
```
make tests
```
The server and client can be started similarly:
```
python -m server
```
or
```
make server
```
and
```
python -m client
```
or
```
make client
```

## Configuration

Both the server and clients receive their configuration through a Yaml file in the top directory of the project.  They are ```server_config.yaml``` and ```client_config.yaml``` respectively.

Alternatively, many of the configuration options in the Yaml files are also available as command line parameters.  Imported Yaml configuration should be considered the default and will be overridden by the command line parameters.  Obtaining a description of command line parameters is as simple as ```python -m server -h``` and ```python -m client -h```.

## Description

### Server

The server is build on top of ```SocketServer.TCPServer```.  The ```SocketServer``` module contains optional mixins for asynchronous request handlers via ```ForkingMixIn``` and ```ThreadingMixIn```.  Since the ```ThreadinMixIn``` simply uses the ```threading``` module, it doesn't not take advantage of multiple cores and could potentially be IO constrained. The ```ForkinMixIn``` does use separate processes, however it does so via ```os.fork()``` which can make interprocess communication difficult.

To counter this, I implemented a mixin that uses the ```multiprocessing``` module, ```MultiprocessMixIn```.  As a result I can easily share ```multiprocessing``` synchronization objects via a ```Manager``` instance.

There is a separate ```Handler``` process for each client connection that is handled. On the parent server process, a separate thread is started to process messages that were queued by the corresponding ```Handler``` process.  Threads were used to process these messages because latency was less important here.  Once all client connections are closed, then the report is generated.

### Client

The client consists of three processes.

1.  The parent processes also provides the heartbeat message to the server.  It is implemented in the ```StorageHeartbeat``` class.  This process is responsible for periodically sending heartbeat reqests to each of its child processes and aggregating their responses (or lack thereof) into a message sent to the server.  This process also manages the runtime and sends a *kill* message to each of the clients signalling them to stop.  Once they have stopped, they will return a messaging indicating such and those will also be aggregated into a message sent to the server.

2.  There are a configurable number of consumer processes ```StorageConsumer``` that will write files of a configurable size) to a configurable location.  Each process has individually configurable file and chunk sizes.  Though the storage location is the same for all ```StorageConsumers``` on a given client, it would be trivial to implement independent storage locations as well.

3.  For each client there is a single ```StorageMonitor``` process.  It looks up the cpu, memory and runtime status of each of the ```StorageConsumer``` processes using their pid via the ```ps``` command

### Communication

All messaging used on this application use a generic ```Message``` class to house the communications.  *Heartbeat*, *kill*, and *done* messages within the client are passed over a ```multiprocessing.Pipe``` between the ```StorageHeartbeat``` class and the child processes.  But status messages from the ```StorageConsumer``` and ```StorageMonitor``` processes use a single queue that is consumed by the ```StorageHeartbeat``` class.

Commnication from the client to the server is done over a socket.  This allows clients to reside on their own machines. Though the payload sent over the socket is still the generic ```Message``` type, they are serialized with ```pickle```, which is sufficient for a naive application such as this.  But for an unsecure network, one would want to use an encrypted protocol, or, at the very least, use some sort of client authentication before processing messages.

The pickled payload is sufficient for serializing the message. However, the messages are prefixed with a simple header indicating the size of the pickled message for ease of demarcating the messages, which would otherwise appear as a continuous stream on the server.
