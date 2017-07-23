# Solidfire/NetApp Programming Exercise

## TODO
    
1.  Better server report
2.  Unit Tests
3.  Document Tests
4.  *README*

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

Both the server and clients receive their configuration through a yaml file in the top directory of the project.  They are ```server_config.yaml``` and ```client_config.yaml``` respectively.

Alternatively, many of the configuration options in the Yaml files are also available as command line parameters.  Imported Yaml configuration should be considered the default and will be overridden by the command line parameters.  Obtaining a description of command line parameters is as simple as.
```python -m server -h```
and
```python -m client -h```

## Description

### Server

The server is build on top of ```SocketServer.TCPServer```.  The ```SocketServer``` module contains optional mixins for asynchronous request handlers via ```ForkingMixIn``` and ```ThreadingMixIn```.  Since the ```ThreadinMixIn``` simply uses the ```threading``` module, it doesn't not take advantage of multiple cores and could potentially be IO constrained. The ```ForkinMixIn``` does use separate processes, however it does so via ```os.fork()``` which can make interprocess communication difficult.  i

To counter this, I implemented a mixin that uses the ```multiprocessing``` module, ```MultiprocessMixIn```.  As a result I can easily share ```multiprocessing``` synchronization objects via a ```Manager``` instance.

The ```MultiprocessingMixIn``` also overrides a few of the *mixin* methods in order to pass a ```Queue``` to the ```Handler``` class, which receives messages on the socket connection and enqueues them for processing by a thread on the server.

There is a separate ```Handler``` process for each client connection that is handled. On the parent server process, a separate thread is started to process messages that were queued by the corresponding ```Handler``` process.  Threads were used to process these messages because latency was less important here.  Once all client connections are closed, then the report is generated.

### Client

blah blah

### Tests

more blahs
